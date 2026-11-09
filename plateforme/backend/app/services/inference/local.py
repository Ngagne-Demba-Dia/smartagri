"""Moteur local : paquets joblib (scikit-learn, LightGBM…) ou ONNX servis depuis MODEL_BUNDLE_DIR.

Un paquet joblib est un pickle : le charger exécute du code. Il n'est donc chargé que s'il se trouve sous
MODEL_BUNDLE_DIR et si son empreinte SHA-256 correspond au registre (`model_registry.sha256`). Les
bibliothèques (joblib, numpy, onnxruntime) sont importées paresseusement.

Formats acceptés :
- estimateur exposant `predict(X)` → une prédiction numérique par ligne ;
- dictionnaire d'estimateurs par quantile (`{"p10": est, "p50": est, "p90": est}`) → un dict par ligne ;
- `.onnx` : première sortie du graphe, entrée float32 de forme (n, nb_variables).
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.inference.base import (
    FeatureRow,
    InferenceError,
    ModelEntry,
    Prediction,
    check_predictions,
    feature_matrix,
)
from app.services.inference.registry import resolve_bundle_path, serving_entry, verify_bundle

JOBLIB_SUFFIXES = frozenset({".joblib", ".pkl"})
ONNX_SUFFIX = ".onnx"
_CACHE_SIZE = 8

_cache: dict[tuple[str, str], Any] = {}
_cache_lock = threading.Lock()


def _load_joblib(path: Path) -> Any:
    try:
        import joblib
    except ImportError as exc:
        raise InferenceError("Paquet « joblib » absent : moteur local indisponible.") from exc
    return joblib.load(path)


def _load_onnx(path: Path) -> Any:
    try:
        import onnxruntime
    except ImportError as exc:
        raise InferenceError("Paquet « onnxruntime » absent : modèles ONNX indisponibles.") from exc
    return onnxruntime.InferenceSession(str(path), providers=["CPUExecutionProvider"])


def load_bundle(path: Path, sha256: str | None) -> Any:
    """Charge (ou relit du cache) un paquet vérifié ; la clé de cache inclut l'empreinte attendue."""
    key = (str(path), (sha256 or "").lower())
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    verify_bundle(path, sha256)
    suffix = path.suffix.lower()
    if suffix in JOBLIB_SUFFIXES:
        model = _load_joblib(path)
    elif suffix == ONNX_SUFFIX:
        model = _load_onnx(path)
    else:
        raise InferenceError(f"Format de paquet non pris en charge : {suffix or 'sans extension'}.")
    with _cache_lock:
        if len(_cache) >= _CACHE_SIZE:
            _cache.pop(next(iter(_cache)))
        _cache[key] = model
    return model


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _numeric_matrix(matrix: list[list[Any]]) -> list[list[float]]:
    try:
        return [[float(value) for value in row] for row in matrix]
    except (TypeError, ValueError) as exc:
        raise InferenceError("Variables non numériques : encodage attendu dans le paquet du modèle.") from exc


def _to_list(values: Any) -> list[Any]:
    return values.tolist() if hasattr(values, "tolist") else list(values)


def run_model(model: Any, matrix: list[list[Any]]) -> list[Any]:
    """Applique un modèle chargé ; renvoie des valeurs brutes (contrôlées ensuite par `check_predictions`)."""
    if isinstance(model, Mapping):
        columns = {name: _to_list(estimator.predict(matrix)) for name, estimator in model.items()}
        return [{name: float(values[i]) for name, values in columns.items()} for i in range(len(matrix))]
    if hasattr(model, "get_inputs"):  # session onnxruntime
        import numpy as np

        array = np.asarray(_numeric_matrix(matrix), dtype=np.float32)
        output = model.run(None, {model.get_inputs()[0].name: array})[0]
        return [float(value) for value in np.asarray(output).reshape(len(matrix), -1)[:, 0]]
    if hasattr(model, "predict"):
        return [float(value) for value in _to_list(model.predict(matrix))]
    raise InferenceError("Paquet chargé sans méthode `predict`.")


class LocalBundleBackend:
    name = "local"
    sources: tuple[str, ...] = ("agriml", "octopus")

    def __init__(self, session: Session, bundle_dir: str) -> None:
        self._session = session
        self._bundle_dir = bundle_dir

    def entry(self, model_name: str) -> ModelEntry:
        return serving_entry(self._session, model_name, self.sources)

    def predict(self, model_name: str, rows: Sequence[FeatureRow]) -> list[Prediction]:
        if not rows:
            return []
        entry = self.entry(model_name)
        matrix = feature_matrix(entry, rows)
        path = resolve_bundle_path(self._bundle_dir, entry.uri)
        try:
            raw = run_model(load_bundle(path, entry.sha256), matrix)
        except InferenceError:
            raise
        except Exception as exc:  # paquet corrompu ou erreur interne du modèle : jamais remontée au client
            raise InferenceError(f"Échec du modèle {entry.name}:{entry.version} ({type(exc).__name__}).") from exc
        return check_predictions(raw, len(rows))

"""Inférence de production à partir des artefacts d'une expérience (même code de variables qu'à l'entraînement).

Usage :
    python -m agriml.predict --run artifacts/yield_regression --input nouvelles.csv --output preds.csv
                             [--history historique.csv]

`--history` : lignes passées des mêmes parcelles / capteurs, nécessaires aux retards et fenêtres glissantes ;
elles servent au calcul des variables puis sont retirées de la sortie.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml

from agriml.config import ExperimentConfig, parse_config
from agriml.ensemble import meta_predict, rank_average, stack_features, weighted_average
from agriml.features.pipeline import build_stateless_features
from agriml.io import read_json, read_table
from agriml.logs import setup_logging
from agriml.metrics import inverse_log1p

logger = logging.getLogger("agriml.predict")
HISTORY_MARKER = "__history__"
WEIGHTED_METHODS = ("mean", "hill_climbing", "weights_opt")


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    cfg: ExperimentConfig
    ensemble: dict[str, Any]
    classes: list | None
    bundles: dict[str, list[dict]]
    meta_model: Any = None

    @property
    def members(self) -> list[str]:
        """Modèles nécessaires à la prédiction finale."""
        ens = self.ensemble
        if ens["type"] == "model":
            return [ens["name"]]
        if ens["name"] in WEIGHTED_METHODS:
            return [name for name, w in ens["weights"].items() if w > 0]
        return list(ens["members"])


def load_run_config(run_dir: str | Path) -> ExperimentConfig:
    raw = yaml.safe_load((Path(run_dir) / "config_resolved.yaml").read_text(encoding="utf-8"))
    return parse_config(raw, root_dir=raw.get("root_dir", "."))


def load_run(run_dir: str | Path) -> RunArtifacts:
    """Charge configuration, ensemble retenu, classes et paquets (transformation + modèle) de chaque pli."""
    run_dir = Path(run_dir)
    cfg = load_run_config(run_dir)
    ensemble = read_json(run_dir / "ensemble.json")
    labels = read_json(run_dir / "label_mapping.json")
    bundles = {}
    for model_dir in sorted((run_dir / "models").iterdir()):
        files = sorted(model_dir.glob("*.joblib"))
        if files:
            bundles[model_dir.name] = [joblib.load(f) for f in files]
    meta_path = run_dir / "meta_model.joblib"
    meta = joblib.load(meta_path) if meta_path.exists() else None
    return RunArtifacts(run_dir, cfg, ensemble, labels.get("classes"), bundles, meta)


def _features(art: RunArtifacts, df: pd.DataFrame, history: pd.DataFrame | None) -> pd.DataFrame:
    frames = [df.assign(**{HISTORY_MARKER: False})]
    if history is not None:
        frames.insert(0, history.drop(columns=[art.cfg.columns.target], errors="ignore").assign(**{HISTORY_MARKER: True}))
    full = build_stateless_features(pd.concat(frames, ignore_index=True), art.cfg)
    return full[~full[HISTORY_MARKER].to_numpy(dtype=bool)].drop(columns=HISTORY_MARKER).reset_index(drop=True)


def predict_model(art: RunArtifacts, name: str, X: pd.DataFrame) -> np.ndarray:
    """Moyenne des modèles de tous les plis et graines (espace d'apprentissage), puis retour à l'échelle cible."""
    if name not in art.bundles:
        raise KeyError(f"Modèle « {name} » absent des artefacts ({sorted(art.bundles)}).")
    preds = [b["model"].predict(b["transformer"].transform(X)) for b in art.bundles[name]]
    mean = np.mean(preds, axis=0)
    return inverse_log1p(mean) if art.cfg.target_transform == "log1p" else mean


def _combine(art: RunArtifacts, preds: dict[str, np.ndarray]) -> np.ndarray:
    ens = art.ensemble
    if ens["type"] == "model":
        return preds[ens["name"]]
    if ens["name"] == "stacking":
        # même ordre de colonnes qu'à l'entraînement (ordre des membres)
        ordered = {name: preds[name] for name in ens["members"]}
        return meta_predict(art.meta_model, stack_features(ordered, art.cfg.task), art.cfg.task)
    if ens["name"] == "rank_average":
        # rangs relatifs au lot scoré : n'a de sens que pour classer (AUC), pas comme probabilité
        return rank_average(preds)
    return weighted_average(preds, ens["weights"])


def predict_frame(art: RunArtifacts, df: pd.DataFrame, history: pd.DataFrame | None = None) -> pd.DataFrame:
    """Prédictions finales (modèle ou ensemble retenu) pour les lignes de `df`."""
    X = _features(art, df, history)
    preds = {name: predict_model(art, name, X) for name in art.members}
    final = _combine(art, preds)
    out = pd.DataFrame({art.cfg.columns.id: X[art.cfg.columns.id].to_numpy()})
    if final.ndim == 2:
        for k, cls in enumerate(art.classes or range(final.shape[1])):
            out[f"proba_{cls}"] = final[:, k]
        return out
    out["prediction"] = final
    threshold = art.ensemble.get("threshold")
    if art.cfg.task == "binary" and threshold is not None:
        out["label"] = np.asarray(art.classes, dtype=object)[(final >= threshold).astype(int)]
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inférence agriml à partir d'un dossier d'artefacts.")
    parser.add_argument("--run", required=True, help="Dossier artifacts/<expérience>.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--history", help="Historique des mêmes groupes (retards / fenêtres).")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    art = load_run(args.run)
    history = read_table(args.history) if args.history else None
    out = predict_frame(art, read_table(args.input), history)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    logger.info("%d prédictions écrites dans %s", len(out), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

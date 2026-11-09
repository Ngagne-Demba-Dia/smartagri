"""Construction et validation stricte du fichier de soumission (format du sample_submission)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd


class SubmissionError(ValueError):
    """Soumission non conforme."""


def build_submission(ids, predictions: np.ndarray, id_column: str, pred_columns: Sequence[str],
                     clip_min: float | None = None, clip_max: float | None = None) -> pd.DataFrame:
    """Assemble la soumission ; `predictions` 1D (une colonne) ou 2D (une colonne par classe)."""
    pred = np.asarray(predictions, dtype=float)
    if clip_min is not None or clip_max is not None:
        pred = np.clip(pred, clip_min, clip_max)
    pred = pred.reshape(-1, 1) if pred.ndim == 1 else pred
    if pred.shape[1] != len(pred_columns):
        raise SubmissionError(f"{pred.shape[1]} colonnes prédites pour {len(pred_columns)} colonnes attendues.")
    data = {id_column: np.asarray(ids)}
    data.update({col: pred[:, j] for j, col in enumerate(pred_columns)})
    return pd.DataFrame(data)


def _check_values(sub: pd.DataFrame, pred_cols: list[str], task: str | None) -> list[str]:
    errors = []
    values = sub[pred_cols]
    if not all(pd.api.types.is_numeric_dtype(values[c]) for c in pred_cols):
        return ["colonnes de prédiction non numériques"]
    arr = values.to_numpy(dtype=float)
    if not np.isfinite(arr).all():
        errors.append(f"{int((~np.isfinite(arr)).sum())} valeurs NaN ou infinies")
    if task in ("binary", "multiclass") and ((arr < 0) | (arr > 1)).any():
        errors.append("probabilités hors de [0, 1]")
    if task == "multiclass" and len(pred_cols) > 1 and not np.allclose(arr.sum(axis=1), 1.0, atol=1e-4):
        errors.append("les probabilités d'une ligne ne somment pas à 1")
    return errors


def validate_submission(sub: pd.DataFrame, sample: pd.DataFrame, id_column: str, task: str | None = None,
                        value_range: tuple[float | None, float | None] | None = None) -> list[str]:
    """Renvoie la liste des écarts au format attendu (vide = soumission valide)."""
    errors: list[str] = []
    if list(sub.columns) != list(sample.columns):
        return [f"colonnes {list(sub.columns)} ≠ attendues {list(sample.columns)}"]
    if len(sub) != len(sample):
        errors.append(f"{len(sub)} lignes au lieu de {len(sample)}")
    if sub[id_column].duplicated().any():
        errors.append(f"{int(sub[id_column].duplicated().sum())} identifiants en double")
    missing = set(sample[id_column].astype(str)) - set(sub[id_column].astype(str))
    extra = set(sub[id_column].astype(str)) - set(sample[id_column].astype(str))
    if missing or extra:
        errors.append(f"identifiants manquants : {len(missing)}, inattendus : {len(extra)}")
    pred_cols = [c for c in sub.columns if c != id_column]
    errors.extend(_check_values(sub, pred_cols, task))
    if value_range is not None and not errors:
        low, high = value_range
        arr = sub[pred_cols].to_numpy(dtype=float)
        if (low is not None and (arr < low).any()) or (high is not None and (arr > high).any()):
            errors.append(f"valeurs hors de la plage [{low}, {high}]")
    return errors


def assert_valid_submission(sub: pd.DataFrame, sample: pd.DataFrame, id_column: str, task: str | None = None,
                            value_range: tuple[float | None, float | None] | None = None) -> None:
    errors = validate_submission(sub, sample, id_column, task, value_range)
    if errors:
        raise SubmissionError("Soumission invalide :\n- " + "\n- ".join(errors))


def align_to_sample(sub: pd.DataFrame, sample: pd.DataFrame, id_column: str) -> pd.DataFrame:
    """Réordonne les lignes comme le sample_submission (certaines plateformes l'exigent)."""
    order = pd.Series(range(len(sample)), index=sample[id_column].astype(str))
    key = sub[id_column].astype(str).map(order)
    return sub.assign(_order=key.to_numpy()).sort_values("_order").drop(columns="_order").reset_index(drop=True)


def write_submission(sub: pd.DataFrame, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    sub.to_csv(p, index=False, float_format="%.6f")
    return p

"""Schémas de validation croisée sans fuite et contrôle automatique des fuites.

Règle d'or en compétition : le découpage de validation doit imiter le découpage public/privé du classement.
- test = nouvelles parcelles             → `group` / `stratified_group` (groupe = parcelle) ;
- test = saisons futures                 → `purged_time` (purge `gap` + `embargo` autour du bloc validé) ;
- test = nouvelles zones géographiques   → `spatial_block` (blocs lat/lon) ;
- test tiré au hasard dans les mêmes lignes → `kfold` / `stratified`.

`check_no_leakage` vérifie a posteriori : recouvrements, groupes partagés, lignes d'entraînement
dans la fenêtre de purge, lignes validées plusieurs fois, plis vides.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedGroupKFold, StratifiedKFold

if TYPE_CHECKING:
    from agriml.config import CVConfig, ExperimentConfig

Split = tuple[np.ndarray, np.ndarray]
DEFAULT_REGRESSION_BINS = 10


class LeakageError(RuntimeError):
    """Découpage de validation qui laisse fuir de l'information."""


def regression_bins(y, n_bins: int = DEFAULT_REGRESSION_BINS) -> np.ndarray:
    """Classes de quantiles (par rang) pour stratifier une cible continue."""
    y = np.asarray(y, dtype=float)
    ranks = pd.Series(y).rank(method="first").to_numpy()
    n_bins = max(2, min(n_bins, len(y) // 2))
    return np.minimum((ranks - 1) * n_bins // len(y), n_bins - 1).astype(int)


def kfold_splits(n_rows: int, n_splits: int, seed: int, shuffle: bool = True) -> list[Split]:
    kf = KFold(n_splits=n_splits, shuffle=shuffle, random_state=seed if shuffle else None)
    return [(tr, va) for tr, va in kf.split(np.zeros(n_rows))]


def stratified_splits(y, n_splits: int, seed: int, shuffle: bool = True) -> list[Split]:
    skf = StratifiedKFold(n_splits=n_splits, shuffle=shuffle, random_state=seed if shuffle else None)
    y = np.asarray(y)
    return [(tr, va) for tr, va in skf.split(np.zeros(len(y)), y)]


def group_splits(groups, n_splits: int, seed: int) -> list[Split]:
    """K-fold par groupes, mélangé par graine puis équilibré en taille (plus grand groupe d'abord)."""
    groups = np.asarray(groups)
    uniq, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    if len(uniq) < n_splits:
        raise ValueError(f"{len(uniq)} groupes pour {n_splits} plis : réduire n_splits.")
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(uniq))
    order = order[np.argsort(-counts[order], kind="stable")]
    fold_of_group = np.empty(len(uniq), dtype=int)
    fold_sizes = np.zeros(n_splits, dtype=int)
    for g in order:
        k = int(np.argmin(fold_sizes))
        fold_of_group[g] = k
        fold_sizes[k] += counts[g]
    fold = fold_of_group[inverse.reshape(-1)]
    idx = np.arange(len(groups))
    return [(idx[fold != k], idx[fold == k]) for k in range(n_splits)]


def stratified_group_splits(y, groups, n_splits: int, seed: int) -> list[Split]:
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    y = np.asarray(y)
    return [(tr, va) for tr, va in sgkf.split(np.zeros(len(y)), y, np.asarray(groups))]


def _as_numeric_time(times) -> np.ndarray:
    """Dates → jours flottants ; nombres (années, jours) inchangés."""
    s = pd.Series(times)
    if pd.api.types.is_datetime64_any_dtype(s):
        return (s - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy() / 86400.0
    if s.dtype == object:
        parsed = pd.to_datetime(s, utc=True, errors="raise").dt.tz_localize(None)
        return (parsed - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy() / 86400.0
    return s.to_numpy(dtype=float)


def purged_time_splits(times, n_splits: int, gap: float = 0.0, embargo: float = 0.0,
                       forward: bool = False) -> list[Split]:
    """Validation temporelle par blocs avec purge.

    - `forward=False` (combinatoire simple) : chaque bloc de temps est validé une fois ; l'entraînement
      utilise le passé (avant `v_start - gap`) ET le futur (après `v_end + embargo`). Toutes les lignes
      reçoivent une prédiction OOF. Adapté quand le test est une période future mais que les saisons
      sont quasi indépendantes (rendement annuel).
    - `forward=True` (walk-forward) : entraînement uniquement sur le passé ; le premier bloc n'est jamais
      validé (OOF = NaN). Plus pessimiste, à préférer pour les séries autocorrélées (capteurs).
    Unités de `gap`/`embargo` : celles de la colonne temps (années, ou jours si dates).
    """
    t = _as_numeric_time(times)
    uniq = np.unique(t)
    n_blocks = n_splits + 1 if forward else n_splits
    if len(uniq) < n_blocks:
        raise ValueError(f"{len(uniq)} instants distincts pour {n_blocks} blocs temporels.")
    blocks = np.array_split(uniq, n_blocks)
    idx = np.arange(len(t))
    splits: list[Split] = []
    for block in blocks[1:] if forward else blocks:
        v_start, v_end = block[0], block[-1]
        valid = (t >= v_start) & (t <= v_end)
        before = t < v_start - gap if gap > 0 else t < v_start
        after = (t > v_end + embargo) if not forward else np.zeros_like(valid)
        train = before | after
        splits.append((idx[train], idx[valid]))
    return splits


def spatial_cells(lat, lon, block_size_deg: float) -> np.ndarray:
    cells = np.column_stack([np.floor(np.asarray(lat, float) / block_size_deg),
                             np.floor(np.asarray(lon, float) / block_size_deg)])
    _, inverse = np.unique(cells, axis=0, return_inverse=True)
    return inverse.reshape(-1)


def spatial_block_splits(lat, lon, y, n_splits: int, seed: int, block_size_deg: float,
                         classification: bool) -> list[Split]:
    """Blocs géographiques (cellules de `block_size_deg` degrés) validés ensemble : teste la généralisation
    à de nouvelles zones et neutralise l'autocorrélation spatiale."""
    cells = spatial_cells(lat, lon, block_size_deg)
    if classification:
        return stratified_group_splits(y, cells, n_splits, seed)
    return group_splits(cells, n_splits, seed)


def make_splits(df: pd.DataFrame, y, cfg: ExperimentConfig, seed: int) -> list[Split]:
    """Construit les plis selon `cfg.cv` (les colonnes requises ont été validées au chargement)."""
    cv: CVConfig = cfg.cv
    cols = cfg.columns
    classification = cfg.task != "regression"
    n = len(df)
    if cv.scheme == "kfold":
        return kfold_splits(n, cv.n_splits, seed, cv.shuffle)
    if cv.scheme == "stratified":
        strata = y if classification else regression_bins(y)
        return stratified_splits(strata, cv.n_splits, seed, cv.shuffle)
    if cv.scheme == "group":
        return group_splits(df[cols.group].to_numpy(), cv.n_splits, seed)
    if cv.scheme == "stratified_group":
        strata = y if classification else regression_bins(y)
        return stratified_group_splits(strata, df[cols.group].to_numpy(), cv.n_splits, seed)
    if cv.scheme == "purged_time":
        return purged_time_splits(df[cols.time].to_numpy(), cv.n_splits, cv.gap, cv.embargo, cv.forward)
    if cv.scheme == "spatial_block":
        strata = y if classification else None
        return spatial_block_splits(df[cols.lat], df[cols.lon], strata, cv.n_splits, seed,
                                    cv.block_size_deg, classification)
    raise ValueError(f"Schéma de validation inconnu : {cv.scheme}")


# --------------------------------------------------------------------------- contrôle des fuites


def _check_time_purge(k: int, tr: np.ndarray, va: np.ndarray, t: np.ndarray, gap: float,
                      embargo: float) -> list[str]:
    v_start, v_end = t[va].min(), t[va].max()
    t_tr = t[tr]
    inside = (t_tr >= v_start - gap) & (t_tr <= v_end + embargo)
    if inside.any():
        return [f"pli {k} : {int(inside.sum())} lignes d'entraînement dans la fenêtre purgée "
                f"[{v_start - gap:g}, {v_end + embargo:g}]"]
    return []


def check_no_leakage(splits: Sequence[Split], n_rows: int, groups=None, times=None,
                     gap: float = 0.0, embargo: float = 0.0) -> list[str]:
    """Renvoie la liste des problèmes détectés (vide = découpage sain)."""
    issues: list[str] = []
    seen_valid = np.zeros(n_rows, dtype=int)
    g = np.asarray(groups) if groups is not None else None
    t = _as_numeric_time(times) if times is not None else None
    for k, (tr, va) in enumerate(splits):
        if len(tr) == 0 or len(va) == 0:
            issues.append(f"pli {k} : ensemble d'entraînement ou de validation vide")
            continue
        overlap = np.intersect1d(tr, va)
        if overlap.size:
            issues.append(f"pli {k} : {overlap.size} lignes à la fois en entraînement et en validation")
        if g is not None:
            shared = np.intersect1d(np.unique(g[tr]), np.unique(g[va]))
            if shared.size:
                issues.append(f"pli {k} : {shared.size} groupes présents des deux côtés (ex. {shared[:3].tolist()})")
        if t is not None:
            issues.extend(_check_time_purge(k, tr, va, t, gap, embargo))
        seen_valid[va] += 1
    if (seen_valid > 1).any():
        issues.append(f"{int((seen_valid > 1).sum())} lignes validées plusieurs fois")
    return issues


def assert_no_leakage(splits: Sequence[Split], n_rows: int, groups=None, times=None,
                      gap: float = 0.0, embargo: float = 0.0) -> None:
    issues = check_no_leakage(splits, n_rows, groups, times, gap, embargo)
    if issues:
        raise LeakageError("Fuite de validation détectée :\n- " + "\n- ".join(issues))


def leakage_context(df: pd.DataFrame, cfg: ExperimentConfig) -> dict:
    """Arguments de `check_no_leakage` adaptés au schéma configuré."""
    cols, cv = cfg.columns, cfg.cv
    ctx: dict = {}
    if cv.scheme in ("group", "stratified_group") and cols.group:
        ctx["groups"] = df[cols.group].to_numpy()
    if cv.scheme == "spatial_block":
        ctx["groups"] = spatial_cells(df[cols.lat], df[cols.lon], cv.block_size_deg)
    if cv.scheme == "purged_time":
        ctx.update(times=df[cols.time].to_numpy(), gap=cv.gap, embargo=cv.embargo)
    return ctx

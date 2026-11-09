"""Variables temporelles sans fuite : retards, fenêtres glissantes, différences et encodage cyclique.

Garanties :
- calcul par groupe (parcelle, capteur) après tri par (groupe, temps) ;
- uniquement le passé : `shift(lag ≥ 1)` ; les fenêtres glissantes excluent l'instant courant par défaut
  (`include_current=False`), indispensable si la colonne est la cible ou corrélée à la cible du jour ;
- l'ordre et l'index d'origine sont restitués.

Piège classique : un retard de la cible (« rendement de l'an dernier ») n'est disponible pour le test
que si l'année précédente est connue à la date de prédiction. Ne jamais l'ajouter si l'écart entre
la fin du train et le test dépasse le retard.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

PERIODS = {"doy": 365.25, "hour": 24.0, "month": 12.0, "dow": 7.0}


def _check_index(df: pd.DataFrame) -> None:
    if not df.index.is_unique:
        raise ValueError("Index non unique : appeler reset_index() avant les variables temporelles.")


def _sorted(df: pd.DataFrame, group: str | None, time: str) -> pd.DataFrame:
    keys = [group, time] if group else [time]
    return df.sort_values(keys, kind="stable")


def add_lag_features(df: pd.DataFrame, columns: Sequence[str], lags: Sequence[int], time: str,
                     group: str | None = None) -> pd.DataFrame:
    """Ajoute `<col>_lag<k>` : valeur k pas de temps plus tôt dans le même groupe."""
    _check_index(df)
    if any(int(k) < 1 for k in lags):
        raise ValueError("Les retards doivent être ≥ 1 (un retard 0 copierait la valeur courante).")
    s = _sorted(df, group, time)
    grouped = s.groupby(group, sort=False) if group else None
    new = {}
    for col in columns:
        for k in lags:
            shifted = grouped[col].shift(int(k)) if grouped is not None else s[col].shift(int(k))
            new[f"{col}_lag{int(k)}"] = shifted
    return df.join(pd.DataFrame(new, index=s.index))


def add_rolling_features(df: pd.DataFrame, columns: Sequence[str], windows: Sequence[int], time: str,
                         group: str | None = None, stats: Sequence[str] = ("mean",),
                         include_current: bool = False) -> pd.DataFrame:
    """Ajoute `<col>_roll<w>_<stat>` sur les `w` derniers pas (passés uniquement si include_current=False)."""
    _check_index(df)
    s = _sorted(df, group, time)
    new = {}
    for col in columns:
        base = s.groupby(group, sort=False)[col].shift(1) if (group and not include_current) else (
            s[col].shift(1) if not include_current else s[col])
        keys = s[group] if group else pd.Series(0, index=s.index)
        for w in windows:
            roll = base.groupby(keys.to_numpy()).rolling(int(w), min_periods=1)
            for stat in stats:
                values = getattr(roll, stat)().reset_index(level=0, drop=True)
                new[f"{col}_roll{int(w)}_{stat}"] = values.reindex(s.index)
    return df.join(pd.DataFrame(new, index=s.index))


def add_diff_features(df: pd.DataFrame, columns: Sequence[str], time: str, group: str | None = None,
                      periods: int = 1) -> pd.DataFrame:
    """Ajoute `<col>_diff<p>` = x(t) − x(t − p) dans le groupe (tendance récente)."""
    _check_index(df)
    s = _sorted(df, group, time)
    new = {}
    for col in columns:
        series = s.groupby(group, sort=False)[col] if group else s[col]
        new[f"{col}_diff{periods}"] = series.diff(periods)
    return df.join(pd.DataFrame(new, index=s.index))


def add_cyclical_features(df: pd.DataFrame, column: str, kind: str = "raw",
                          period: float | None = None) -> pd.DataFrame:
    """Encode une variable cyclique en (sin, cos) : jour de l'année, heure, mois ou valeur brute + période."""
    out = df.copy()
    values = df[column]
    if kind in ("doy", "hour", "month", "dow") and not pd.api.types.is_numeric_dtype(values):
        dt = pd.to_datetime(values, utc=True)
        values = {"doy": dt.dt.dayofyear, "hour": dt.dt.hour, "month": dt.dt.month, "dow": dt.dt.dayofweek}[kind]
    p = period or PERIODS.get(kind)
    if p is None:
        raise ValueError(f"Période requise pour l'encodage cyclique de « {column} » (kind={kind}).")
    angle = 2 * np.pi * np.asarray(values, dtype=float) / p
    out[f"{column}_sin"] = np.sin(angle)
    out[f"{column}_cos"] = np.cos(angle)
    return out

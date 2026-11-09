"""Indices de télédétection (NDVI, EVI) et résumé de séries temporelles d'indices par parcelle.

Les séries sont fournies en colonnes larges (`ndvi_1 … ndvi_n`, dates d'acquisition ordonnées) ; les
valeurs manquantes (nuages) sont interpolées ligne par ligne avant le calcul des résumés.
"""

from __future__ import annotations

import re
import warnings

import numpy as np
import pandas as pd

EVI_G, EVI_C1, EVI_C2, EVI_L = 2.5, 6.0, 7.5, 1.0


def ndvi(nir, red) -> np.ndarray:
    nir, red = np.asarray(nir, dtype=float), np.asarray(red, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(nir + red != 0, (nir - red) / (nir + red), np.nan)


def evi(nir, red, blue) -> np.ndarray:
    nir, red, blue = (np.asarray(a, dtype=float) for a in (nir, red, blue))
    denom = nir + EVI_C1 * red - EVI_C2 * blue + EVI_L
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denom != 0, EVI_G * (nir - red) / denom, np.nan)


def series_columns(df: pd.DataFrame, prefix: str) -> list[str]:
    """Colonnes `<prefix><n>` triées par n."""
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    matches = [(int(m.group(1)), c) for c in df.columns if (m := pattern.match(str(c)))]
    return [c for _, c in sorted(matches)]


def _interpolate_rows(values: np.ndarray) -> np.ndarray:
    return pd.DataFrame(values).interpolate(axis=1, limit_direction="both").to_numpy(dtype=float)


def _slopes(filled: np.ndarray, peak: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pente moyenne de verdissement (début → pic) et de sénescence (pic → fin)."""
    n = filled.shape[1]
    rows = np.arange(len(filled))
    peak_val = filled[rows, peak]
    green = np.where(peak > 0, (peak_val - filled[:, 0]) / np.maximum(peak, 1), 0.0)
    senes = np.where(peak < n - 1, (filled[:, -1] - peak_val) / np.maximum(n - 1 - peak, 1), 0.0)
    return green, senes


def add_series_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Ajoute `<stem>_mean`, max, min, std, amplitude, peak_idx, integral, pentes et obs_frac
    (stem = préfixe sans « _ » final : « ndvi_ » → « ndvi_mean »)."""
    cols = series_columns(df, prefix)
    if len(cols) < 2:
        raise ValueError(f"Série « {prefix} » : au moins deux colonnes {prefix}1, {prefix}2… attendues.")
    raw = df[cols].to_numpy(dtype=float)
    filled = _interpolate_rows(raw)
    all_nan = np.isnan(filled).all(axis=1)
    safe = np.where(np.isnan(filled), 0.0, filled)
    peak = np.argmax(safe, axis=1)
    green, senes = _slopes(safe, peak)
    out = df.copy()
    stem = prefix.rstrip("_")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        feats = {
            "mean": np.nanmean(filled, axis=1), "max": np.nanmax(filled, axis=1),
            "min": np.nanmin(filled, axis=1), "std": np.nanstd(filled, axis=1),
        }
    feats["amplitude"] = feats["max"] - feats["min"]
    feats["peak_idx"] = peak.astype(float)
    feats["integral"] = np.trapezoid(safe, axis=1)
    feats["greenup_slope"] = green
    feats["senescence_slope"] = senes
    feats["obs_frac"] = (~np.isnan(raw)).mean(axis=1)
    for name, values in feats.items():
        values = np.asarray(values, dtype=float)
        out[f"{stem}_{name}"] = np.where(all_nan & (name != "obs_frac"), np.nan, values)
    return out

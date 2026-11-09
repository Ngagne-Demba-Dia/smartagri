"""Correction statistique des prévisions météo numériques (MOS, Model Output Statistics) par station.

Principe : apprendre l'erreur obs − prévision brute en fonction de l'échéance, de l'heure de validité, de la saison
et des sorties du modèle numérique ; la prévision corrigée = brute + erreur prédite. Un modèle par échéance
(`lead_buckets`) reproduit le MOS classique ; un seul modèle avec l'échéance en variable est plus économe.

Validation : coupure temporelle sur l'heure d'émission avec un écart ≥ plus grande échéance, pour qu'aucune
observation de la période testée ne serve à l'apprentissage.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from agriml.cv import purged_time_splits
from agriml.metrics import get_metric

HOURS_PER_DAY = 24
DAYS_PER_YEAR = 365.25


@dataclass(frozen=True)
class MosConfig:
    station: str = "station_id"
    issue_time: str = "issue_time"
    valid_time: str = "valid_time"
    lead: str = "lead_h"
    raw: str = "nwp_temp_c"
    observed: str = "obs_temp_c"
    predictors: tuple[str, ...] = ("nwp_temp_c", "nwp_rh_pct", "nwp_wind_ms")
    lead_buckets: tuple[tuple[int, int], ...] = ((0, 24), (25, 48), (49, 72))
    n_splits: int = 4
    params: dict[str, Any] = field(default_factory=lambda: {"max_iter": 200, "learning_rate": 0.05,
                                                            "max_leaf_nodes": 15})
    seed: int = 42


def build_mos_frame(df: pd.DataFrame, cfg: MosConfig) -> pd.DataFrame:
    """Ajoute heure / jour de l'année cycliques (heure de validité), code station et résidu cible."""
    out = df.copy()
    valid = pd.to_datetime(out[cfg.valid_time], utc=True)
    out[cfg.issue_time] = pd.to_datetime(out[cfg.issue_time], utc=True)
    out["hour_sin"], out["hour_cos"] = np.sin(2 * np.pi * valid.dt.hour / 24), np.cos(2 * np.pi * valid.dt.hour / 24)
    out["doy_sin"] = np.sin(2 * np.pi * valid.dt.dayofyear / DAYS_PER_YEAR)
    out["doy_cos"] = np.cos(2 * np.pi * valid.dt.dayofyear / DAYS_PER_YEAR)
    out["station_code"] = out[cfg.station].astype("category").cat.codes
    if cfg.observed in out:
        out["residual"] = out[cfg.observed] - out[cfg.raw]
    return out


def mos_features(cfg: MosConfig) -> list[str]:
    return [*cfg.predictors, cfg.lead, "hour_sin", "hour_cos", "doy_sin", "doy_cos", "station_code"]


class MosCorrector:
    """Un HistGradientBoosting par tranche d'échéance, appris sur le résidu (station = variable catégorielle)."""

    def __init__(self, cfg: MosConfig):
        self.cfg = cfg
        self.models: dict[tuple[int, int], HistGradientBoostingRegressor] = {}

    def _bucket_masks(self, frame: pd.DataFrame):
        for lo, hi in self.cfg.lead_buckets:
            yield (lo, hi), frame[self.cfg.lead].between(lo, hi).to_numpy()

    def fit(self, frame: pd.DataFrame) -> MosCorrector:
        feats = mos_features(self.cfg)
        cat = [feats.index("station_code")]
        for bucket, m in self._bucket_masks(frame):
            if m.sum() == 0:
                continue
            model = HistGradientBoostingRegressor(random_state=self.cfg.seed, categorical_features=cat, **self.cfg.params)
            self.models[bucket] = model.fit(frame.loc[m, feats], frame.loc[m, "residual"])
        return self

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """Prévision corrigée ; échéance hors tranches apprises → prévision brute inchangée."""
        corrected = frame[self.cfg.raw].to_numpy(dtype=float).copy()
        for bucket, m in self._bucket_masks(frame):
            if bucket in self.models and m.any():
                corrected[m] += self.models[bucket].predict(frame.loc[m, mos_features(self.cfg)])
        return corrected


def evaluate_mos(df: pd.DataFrame, cfg: MosConfig, leads: Sequence[int] | None = None) -> dict[str, Any]:
    """RMSE brute vs corrigée (global et par échéance) en validation temporelle purgée (walk-forward)."""
    rmse = get_metric("rmse")
    frame = build_mos_frame(df, cfg)
    days = (frame[cfg.issue_time].dt.tz_convert(None) - pd.Timestamp("1970-01-01")).dt.total_seconds() / 86400.0
    gap_days = frame[cfg.lead].max() / HOURS_PER_DAY
    corrected = np.full(len(frame), np.nan)
    for tr, va in purged_time_splits(days.to_numpy(), cfg.n_splits, gap=gap_days, forward=True):
        corrected[va] = MosCorrector(cfg).fit(frame.iloc[tr]).predict(frame.iloc[va])
    ok = ~np.isnan(corrected)
    obs, raw = frame[cfg.observed].to_numpy(), frame[cfg.raw].to_numpy()
    per_lead = {}
    for lead in leads or sorted(frame[cfg.lead].unique()):
        m = ok & (frame[cfg.lead].to_numpy() == lead)
        if m.any():
            per_lead[int(lead)] = {"raw_rmse": rmse(obs[m], raw[m]), "mos_rmse": rmse(obs[m], corrected[m])}
    return {"raw_rmse": rmse(obs[ok], raw[ok]), "mos_rmse": rmse(obs[ok], corrected[ok]),
            "n_validated": int(ok.sum()), "per_lead": per_lead}

"""Prévision de l'humidité du sol à 24/48/72 h à partir de la télémétrie (contrat telemetry.v1).

Stratégie « directe » : un modèle par horizon, qui prédit la variation y(t+h) − y(t) (plus stable que le niveau).
Validation : walk-forward purgé, écart ≥ plus grand horizon (la cible de la dernière ligne d'entraînement ne
chevauche jamais la période validée). Référence obligatoire : la persistance y(t+h) = y(t).

La prévision est conditionnelle à la politique d'arrosage courante (seuils start/stop en variables) : changer les
seuils d'un boîtier change la dynamique future, il faut alors réévaluer le modèle.

Usage : python -m agriml.forecast.soil_moisture --config configs/soil_moisture_forecast.yaml
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from agriml.config import dataclass_from_yaml
from agriml.cv import purged_time_splits
from agriml.io import read_table, write_json, write_table
from agriml.logs import setup_logging
from agriml.metrics import get_metric

logger = logging.getLogger("agriml.forecast.soil_moisture")
HOURS_PER_DAY = 24
INTERPOLATE_LIMIT_H = 3  # trous capteur ≤ 3 h comblés ; au-delà, la ligne reste manquante


@dataclass(frozen=True)
class SoilForecastConfig:
    name: str = "soil_moisture_forecast"
    data: str = "data/synthetic/telemetry/telemetry.csv"
    device: str = "device_id"
    time: str = "ts"
    target: str = "soil_moisture_pct"
    horizons: tuple[int, ...] = (24, 48, 72)
    lags: tuple[int, ...] = (1, 3, 6, 12, 24)
    windows: tuple[int, ...] = (6, 24)
    exog: tuple[str, ...] = ("air_temp_c", "air_humidity_pct", "pump_on", "rain_mm")
    static: tuple[str, ...] = ("threshold_start_pct", "threshold_stop_pct")
    n_splits: int = 4
    gap_hours: int = 72
    params: dict[str, Any] = field(default_factory=lambda: {"max_iter": 300, "learning_rate": 0.05,
                                                            "max_leaf_nodes": 31, "l2_regularization": 1.0})
    seed: int = 42
    output_dir: str = "artifacts"
    root_dir: str = "."

    def __post_init__(self) -> None:
        if self.gap_hours < max(self.horizons):
            raise ValueError(f"gap_hours ({self.gap_hours}) doit être ≥ plus grand horizon ({max(self.horizons)}).")

    @classmethod
    def from_yaml(cls, path: str | Path) -> SoilForecastConfig:
        return dataclass_from_yaml(cls, path)

    def resolve(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else Path(self.root_dir) / p


def resample_hourly(df: pd.DataFrame, cfg: SoilForecastConfig) -> pd.DataFrame:
    """Grille horaire régulière par boîtier ; mesures invalides (soil_sensor_ok=False) mises à NaN."""
    data = df.copy()
    data[cfg.time] = pd.to_datetime(data[cfg.time], utc=True)
    if "soil_sensor_ok" in data:
        data.loc[~data["soil_sensor_ok"].astype(bool), cfg.target] = np.nan
    cols = [c for c in (cfg.target, *cfg.exog, *cfg.static) if c in data]
    data[cols] = data[cols].astype(float)
    frames = []
    for device, grp in data.groupby(cfg.device, sort=True):
        hourly = grp.set_index(cfg.time)[cols].resample("1h").mean()
        hourly[cfg.target] = hourly[cfg.target].interpolate(limit=INTERPOLATE_LIMIT_H, limit_area="inside")
        hourly[list(cfg.static)] = hourly[list(cfg.static)].ffill()
        frames.append(hourly.reset_index().assign(**{cfg.device: device}))
    return pd.concat(frames, ignore_index=True)


def _device_features(g: pd.DataFrame, cfg: SoilForecastConfig) -> dict[str, pd.Series]:
    y = g[cfg.target]
    feats: dict[str, pd.Series] = {"y_now": y}
    feats.update({f"y_lag{k}": y.shift(k) for k in cfg.lags})
    feats.update({f"y_diff{k}": y - y.shift(k) for k in cfg.lags})
    for w in cfg.windows:
        feats[f"y_mean{w}"] = y.rolling(w, min_periods=1).mean()
        for col in cfg.exog:
            if col in g:
                feats[f"{col}_mean{w}"] = g[col].rolling(w, min_periods=1).mean()
    feats.update({col: g[col] for col in (*cfg.exog, *cfg.static) if col in g})
    feats["dist_to_start"] = y - g[cfg.static[0]] if cfg.static and cfg.static[0] in g else y * np.nan
    return feats


def make_supervised(hourly: pd.DataFrame, cfg: SoilForecastConfig) -> pd.DataFrame:
    """Variables connues à t (passé uniquement) + cibles `delta_h{h}` = y(t+h) − y(t), par boîtier."""
    frames = []
    for device, g in hourly.groupby(cfg.device, sort=True):
        g = g.sort_values(cfg.time).reset_index(drop=True)
        feats = _device_features(g, cfg)
        hour = g[cfg.time].dt.hour
        feats["hour_sin"], feats["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
        feats.update({f"delta_h{h}": g[cfg.target].shift(-h) - g[cfg.target] for h in cfg.horizons})
        frames.append(pd.DataFrame(feats).assign(**{cfg.device: device, cfg.time: g[cfg.time]}))
    sup = pd.concat(frames, ignore_index=True)
    return sup[sup["y_now"].notna()].reset_index(drop=True)


def feature_columns(sup: pd.DataFrame, cfg: SoilForecastConfig) -> list[str]:
    return [c for c in sup.columns if c not in (cfg.device, cfg.time) and not c.startswith("delta_h")]


class DirectMultiHorizonForecaster:
    """Un HistGradientBoosting par horizon ; prédit le niveau y(t) + Δ̂_h, borné à [0, 100] %."""

    def __init__(self, horizons: Sequence[int], params: dict[str, Any] | None = None, seed: int = 42):
        self.horizons = tuple(horizons)
        self.params = dict(params or {})
        self.seed = seed
        self.models: dict[int, HistGradientBoostingRegressor] = {}
        self.features: list[str] = []

    def fit(self, X: pd.DataFrame, deltas: pd.DataFrame) -> DirectMultiHorizonForecaster:
        self.features = list(X.columns)
        for h in self.horizons:
            ok = deltas[f"delta_h{h}"].notna().to_numpy()
            model = HistGradientBoostingRegressor(random_state=self.seed, **self.params)
            self.models[h] = model.fit(X[ok], deltas[f"delta_h{h}"][ok])
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X[self.features]
        now = X["y_now"].to_numpy()
        return pd.DataFrame({f"pred_h{h}": np.clip(now + m.predict(X), 0.0, 100.0) for h, m in self.models.items()},
                            index=X.index)


def _hours_since_epoch(times: pd.Series) -> np.ndarray:
    return (times.dt.tz_convert(None) - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy() / 3600.0


def cross_validate(sup: pd.DataFrame, cfg: SoilForecastConfig) -> tuple[dict[str, Any], pd.DataFrame]:
    """Walk-forward purgé ; renvoie (scores modèle vs persistance par horizon, OOF)."""
    rmse = get_metric("rmse")
    feats = feature_columns(sup, cfg)
    splits = purged_time_splits(_hours_since_epoch(sup[cfg.time]), cfg.n_splits, gap=cfg.gap_hours, forward=True)
    oof = pd.DataFrame(np.nan, index=sup.index, columns=[f"pred_h{h}" for h in cfg.horizons])
    for tr, va in splits:
        model = DirectMultiHorizonForecaster(cfg.horizons, cfg.params, cfg.seed)
        model.fit(sup.loc[tr, feats], sup.loc[tr, [f"delta_h{h}" for h in cfg.horizons]])
        oof.loc[va] = model.predict(sup.loc[va, feats]).to_numpy()
    scores: dict[str, Any] = {}
    for h in cfg.horizons:
        truth = sup["y_now"] + sup[f"delta_h{h}"]
        ok = (truth.notna() & oof[f"pred_h{h}"].notna()).to_numpy()
        model_rmse = rmse(truth[ok].to_numpy(), oof.loc[ok, f"pred_h{h}"].to_numpy())
        persistence = rmse(truth[ok].to_numpy(), sup.loc[ok, "y_now"].to_numpy())
        scores[f"h{h}"] = {"rmse": model_rmse, "persistence_rmse": persistence,
                           "skill": 1 - model_rmse / persistence if persistence else None, "n": int(ok.sum())}
    return scores, oof


def train_forecaster(cfg: SoilForecastConfig) -> dict[str, Any]:
    sup = make_supervised(resample_hourly(read_table(cfg.resolve(cfg.data)), cfg), cfg)
    scores, oof = cross_validate(sup, cfg)
    feats = feature_columns(sup, cfg)
    final = DirectMultiHorizonForecaster(cfg.horizons, cfg.params, cfg.seed)
    final.fit(sup[feats], sup[[f"delta_h{h}" for h in cfg.horizons]])
    run_dir = Path(cfg.resolve(cfg.output_dir)) / cfg.name
    run_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"config": cfg, "model": final}, run_dir / "forecaster.joblib")
    write_table(pd.concat([sup[[cfg.device, cfg.time, "y_now"]], oof], axis=1), run_dir / "oof.parquet")
    write_json({"experiment": cfg.name, "horizons": scores, "n_rows": len(sup), "features": feats},
               run_dir / "cv_scores.json")
    return scores


def forecast_latest(bundle: dict[str, Any], telemetry: pd.DataFrame) -> pd.DataFrame:
    """Production : prévision depuis la dernière mesure valide de chaque boîtier (historique ≥ 24 h conseillé)."""
    cfg, model = bundle["config"], bundle["model"]
    sup = make_supervised(resample_hourly(telemetry, cfg), cfg)
    last = sup.sort_values(cfg.time).groupby(cfg.device, sort=True).tail(1)
    preds = model.predict(last[feature_columns(sup, cfg)])
    return pd.concat([last[[cfg.device, cfg.time, "y_now", *cfg.static]], preds], axis=1).reset_index(drop=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prévision d'humidité du sol 24–72 h (télémétrie).")
    parser.add_argument("--config", required=True)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    for h, s in train_forecaster(SoilForecastConfig.from_yaml(args.config)).items():
        logger.info("%s : RMSE %.3f vs persistance %.3f (skill %.1f %%, n=%d)", h, s["rmse"],
                    s["persistence_rmse"], 100 * (s["skill"] or 0), s["n"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

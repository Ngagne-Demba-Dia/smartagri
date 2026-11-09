"""Configuration d'expérience : YAML → dataclasses figées et validées.

Les chemins relatifs sont résolus depuis la racine du projet ML (dossier parent de « configs/ »),
quel que soit le répertoire courant. Une configuration invalide lève `ConfigError` avec un message clair.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from agriml.metrics import get_metric

TASKS = ("regression", "binary", "multiclass")
CV_SCHEMES = ("kfold", "stratified", "group", "stratified_group", "purged_time", "spatial_block")
ENSEMBLE_METHODS = ("none", "mean", "rank_average", "hill_climbing", "weights_opt", "stacking")
MODEL_KINDS = ("ridge", "logreg", "hgb", "rf", "et", "xgb", "lgbm", "catboost", "torch_mlp", "keras_mlp")
FEATURE_BLOCKS = ("agronomy", "remote_sensing", "temporal", "date_cyclical", "target_encoding")
TARGET_TRANSFORMS = ("none", "log1p")
EARLY_STOPPING_MODES = ("inner", "valid", "none")


class ConfigError(ValueError):
    """Configuration invalide."""


def _empty_mapping() -> Mapping[str, Any]:
    return MappingProxyType({})


def freeze(value: Any) -> Any:
    """Rend une structure YAML immuable (dict → MappingProxyType, list → tuple)."""
    if isinstance(value, Mapping):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, list | tuple):
        return tuple(freeze(v) for v in value)
    return value


def thaw(value: Any) -> Any:
    """Inverse de `freeze` : structures Python simples, sérialisables en YAML/JSON."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: thaw(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Mapping):
        return {k: thaw(v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return [thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class DataConfig:
    train: str
    test: str | None = None
    sample_submission: str | None = None
    test_labels: str | None = None  # holdout figé : servi uniquement au rapport, jamais à l'entraînement


@dataclass(frozen=True)
class ColumnsConfig:
    id: str
    target: str
    group: str | None = None
    time: str | None = None
    lat: str | None = None
    lon: str | None = None
    categorical: tuple[str, ...] = ()
    drop: tuple[str, ...] = ()


@dataclass(frozen=True)
class CVConfig:
    scheme: str = "kfold"
    n_splits: int = 5
    gap: float = 0.0
    embargo: float = 0.0
    forward: bool = False
    block_size_deg: float = 0.25
    shuffle: bool = True


@dataclass(frozen=True)
class FeaturesConfig:
    blocks: tuple[str, ...] = ()
    include_time: bool = False
    agronomy: Mapping[str, Any] = field(default_factory=_empty_mapping)
    remote_sensing: Mapping[str, Any] = field(default_factory=_empty_mapping)
    temporal: Mapping[str, Any] = field(default_factory=_empty_mapping)
    date_cyclical: tuple[Mapping[str, Any], ...] = ()
    target_encoding: Mapping[str, Any] = field(default_factory=_empty_mapping)


@dataclass(frozen=True)
class ModelConfig:
    name: str
    kind: str
    params: Mapping[str, Any] = field(default_factory=_empty_mapping)
    search_space: Mapping[str, Any] = field(default_factory=_empty_mapping)
    enabled: bool = True
    early_stopping: str = "inner"


@dataclass(frozen=True)
class TuningConfig:
    enabled: bool = False
    models: tuple[str, ...] = ()
    n_trials: int = 20
    timeout_s: float | None = None


@dataclass(frozen=True)
class EnsembleConfig:
    method: str = "hill_climbing"
    n_iter: int = 50


@dataclass(frozen=True)
class SubmissionConfig:
    pred_columns: tuple[str, ...] = ()
    clip_min: float | None = None
    clip_max: float | None = None
    file_name: str = "submission.csv"


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    task: str
    metric: str
    data: DataConfig
    columns: ColumnsConfig
    cv: CVConfig
    features: FeaturesConfig
    models: tuple[ModelConfig, ...]
    tuning: TuningConfig = field(default_factory=TuningConfig)
    ensemble: EnsembleConfig = field(default_factory=EnsembleConfig)
    submission: SubmissionConfig = field(default_factory=SubmissionConfig)
    seeds: tuple[int, ...] = (42,)
    target_transform: str = "none"
    output_dir: str = "artifacts"
    root_dir: str = "."

    @property
    def greater_is_better(self) -> bool:
        return get_metric(self.metric).greater_is_better

    @property
    def run_dir(self) -> Path:
        return self.resolve(self.output_dir) / self.name

    def resolve(self, path: str | None) -> Path | None:
        if path is None:
            return None
        p = Path(path)
        return p if p.is_absolute() else Path(self.root_dir) / p

    def enabled_models(self) -> tuple[ModelConfig, ...]:
        return tuple(m for m in self.models if m.enabled)


# --------------------------------------------------------------------------- lecture


def _require(raw: Mapping, key: str, ctx: str) -> Any:
    if raw.get(key) in (None, ""):
        raise ConfigError(f"{ctx} : clé obligatoire « {key} » manquante.")
    return raw[key]


def _tuple(value: Any) -> tuple:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _parse_columns(raw: Mapping) -> ColumnsConfig:
    return ColumnsConfig(
        id=str(_require(raw, "id", "columns")),
        target=str(_require(raw, "target", "columns")),
        group=raw.get("group"),
        time=raw.get("time"),
        lat=raw.get("lat"),
        lon=raw.get("lon"),
        categorical=_tuple(raw.get("categorical")),
        drop=_tuple(raw.get("drop")),
    )


def _parse_features(raw: Mapping) -> FeaturesConfig:
    return FeaturesConfig(
        blocks=_tuple(raw.get("blocks")),
        include_time=bool(raw.get("include_time", False)),
        agronomy=freeze(raw.get("agronomy") or {}),
        remote_sensing=freeze(raw.get("remote_sensing") or {}),
        temporal=freeze(raw.get("temporal") or {}),
        date_cyclical=freeze(list(raw.get("date_cyclical") or [])),
        target_encoding=freeze(raw.get("target_encoding") or {}),
    )


def _parse_models(raw_models: Any) -> tuple[ModelConfig, ...]:
    if not raw_models:
        raise ConfigError("models : au moins un modèle est requis.")
    models: list[ModelConfig] = []
    for i, m in enumerate(raw_models):
        ctx = f"models[{i}]"
        models.append(
            ModelConfig(
                name=str(_require(m, "name", ctx)),
                kind=str(_require(m, "kind", ctx)),
                params=freeze(dict(m.get("params") or {})),
                search_space=freeze(dict(m.get("search_space") or {})),
                enabled=bool(m.get("enabled", True)),
                early_stopping=str(m.get("early_stopping", "inner")),
            )
        )
    return tuple(models)


def _parse_tuning(raw: Mapping) -> TuningConfig:
    timeout = raw.get("timeout_s")
    return TuningConfig(
        enabled=bool(raw.get("enabled", False)),
        models=_tuple(raw.get("models")),
        n_trials=int(raw.get("n_trials", 20)),
        timeout_s=float(timeout) if timeout is not None else None,
    )


def _parse_submission(raw: Mapping) -> SubmissionConfig:
    return SubmissionConfig(
        pred_columns=_tuple(raw.get("pred_columns")),
        clip_min=raw.get("clip_min"),
        clip_max=raw.get("clip_max"),
        file_name=str(raw.get("file_name", "submission.csv")),
    )


def parse_config(raw: Mapping[str, Any], root_dir: str | Path = ".") -> ExperimentConfig:
    """Construit et valide une configuration à partir d'un dictionnaire YAML."""
    data_raw = _require(raw, "data", "racine")
    cv_raw = dict(raw.get("cv") or {})
    cfg = ExperimentConfig(
        name=str(_require(raw, "name", "racine")),
        task=str(_require(raw, "task", "racine")),
        metric=str(_require(raw, "metric", "racine")).lower(),
        data=DataConfig(
            train=str(_require(data_raw, "train", "data")),
            test=data_raw.get("test"),
            sample_submission=data_raw.get("sample_submission"),
            test_labels=data_raw.get("test_labels"),
        ),
        columns=_parse_columns(_require(raw, "columns", "racine")),
        cv=CVConfig(**cv_raw),
        features=_parse_features(raw.get("features") or {}),
        models=_parse_models(raw.get("models")),
        tuning=_parse_tuning(raw.get("tuning") or {}),
        ensemble=EnsembleConfig(**dict(raw.get("ensemble") or {})),
        submission=_parse_submission(raw.get("submission") or {}),
        seeds=tuple(int(s) for s in raw.get("seeds", (42,))),
        target_transform=str(raw.get("target_transform", "none")),
        output_dir=str(raw.get("output_dir", "artifacts")),
        root_dir=str(raw.get("root_dir") or root_dir),
    )
    validate_config(cfg, metric_direction=raw.get("metric_direction"))
    return cfg


def default_root_dir(config_path: Path) -> Path:
    """Racine du projet ML : parent de « configs/ » si la configuration s'y trouve."""
    parent = config_path.resolve().parent
    return parent.parent if parent.name == "configs" else parent


def load_config(path: str | Path) -> ExperimentConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Fichier de configuration introuvable : {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    try:
        return parse_config(raw, root_dir=default_root_dir(p))
    except TypeError as exc:  # clé inconnue dans une sous-section
        raise ConfigError(f"{p.name} : {exc}") from exc


def dataclass_from_yaml(cls: type, path: str | Path):
    """Instancie une dataclass de configuration « plate » (prévision, vision) depuis un YAML.

    Listes → tuples (dataclasses figées) ; clés inconnues refusées ; `root_dir` = parent de « configs/ ».
    """
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Fichier de configuration introuvable : {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    unknown = set(raw) - {f.name for f in dataclasses.fields(cls)}
    if unknown:
        raise ConfigError(f"{p.name} : clés inconnues {sorted(unknown)}")
    values = {k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()}
    values.setdefault("root_dir", str(default_root_dir(p)))
    return cls(**values)


def config_to_dict(cfg: ExperimentConfig) -> dict[str, Any]:
    return thaw(cfg)


def dump_config(cfg: ExperimentConfig, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(config_to_dict(cfg), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- validation


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigError(message)


def _validate_cv(cfg: ExperimentConfig) -> None:
    cv, cols = cfg.cv, cfg.columns
    _check(cv.scheme in CV_SCHEMES, f"cv.scheme « {cv.scheme} » inconnu ({', '.join(CV_SCHEMES)}).")
    _check(cv.n_splits >= 2, "cv.n_splits doit être ≥ 2.")
    _check(cv.gap >= 0 and cv.embargo >= 0, "cv.gap et cv.embargo doivent être ≥ 0.")
    if cv.scheme in ("group", "stratified_group"):
        _check(bool(cols.group), f"cv.scheme={cv.scheme} exige columns.group.")
    if cv.scheme == "purged_time":
        _check(bool(cols.time), "cv.scheme=purged_time exige columns.time.")
    if cv.scheme == "spatial_block":
        _check(bool(cols.lat and cols.lon), "cv.scheme=spatial_block exige columns.lat et columns.lon.")
        _check(cv.block_size_deg > 0, "cv.block_size_deg doit être > 0.")


def _validate_models(cfg: ExperimentConfig) -> None:
    names = [m.name for m in cfg.models]
    _check(len(names) == len(set(names)), f"models : noms en double ({names}).")
    for m in cfg.models:
        _check(m.kind in MODEL_KINDS, f"models.{m.name} : kind « {m.kind} » inconnu ({', '.join(MODEL_KINDS)}).")
        _check(m.early_stopping in EARLY_STOPPING_MODES, f"models.{m.name} : early_stopping invalide.")
        _check(cfg.task == "regression" or m.kind != "ridge", f"models.{m.name} : ridge réservé à la régression.")
        _check(cfg.task != "regression" or m.kind != "logreg", f"models.{m.name} : logreg réservé au classement.")
    _check(bool(cfg.enabled_models()), "models : aucun modèle activé.")
    for name in cfg.tuning.models:
        _check(name in names, f"tuning.models : modèle « {name} » absent de models.")


def validate_config(cfg: ExperimentConfig, metric_direction: str | None = None) -> None:
    _check(cfg.task in TASKS, f"task « {cfg.task} » inconnue ({', '.join(TASKS)}).")
    try:
        metric = get_metric(cfg.metric)
    except KeyError as exc:
        raise ConfigError(str(exc)) from exc
    _check(cfg.task in metric.tasks, f"La métrique {metric.name} ne s'applique pas à la tâche {cfg.task}.")
    if metric_direction is not None:
        _check(metric_direction == metric.direction,
               f"metric_direction={metric_direction} incohérent : {metric.name} se {metric.direction}.")
    _validate_cv(cfg)
    _validate_models(cfg)
    unknown = set(cfg.features.blocks) - set(FEATURE_BLOCKS)
    _check(not unknown, f"features.blocks inconnus : {sorted(unknown)}.")
    if "temporal" in cfg.features.blocks:
        _check(bool(cfg.features.temporal.get("columns")), "features.temporal.columns est requis.")
    _check(cfg.ensemble.method in ENSEMBLE_METHODS, f"ensemble.method inconnu ({', '.join(ENSEMBLE_METHODS)}).")
    _check(cfg.target_transform in TARGET_TRANSFORMS, f"target_transform inconnu ({TARGET_TRANSFORMS}).")
    _check(cfg.target_transform == "none" or cfg.task == "regression", "target_transform réservé à la régression.")
    _check(len(cfg.seeds) >= 1, "seeds : au moins une graine.")

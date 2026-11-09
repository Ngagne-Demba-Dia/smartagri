"""Configuration de l'entraînement vision (classification de maladies foliaires, images ESP32-CAM / téléphone)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agriml.config import ConfigError, dataclass_from_yaml

BACKENDS = ("auto", "timm", "hf", "torchvision")


@dataclass(frozen=True)
class VisionConfig:
    name: str = "vision_disease"
    data_dir: str = "data/synthetic/images"
    metadata: str = "metadata.csv"
    path_col: str = "path"
    label_col: str = "label"
    group_col: str = "plant_id"
    classes: tuple[str, ...] = ("sain", "suspect", "malade")
    model_name: str = "mobilenet_v3_small"
    backend: str = "auto"
    pretrained: bool = False
    image_size: int = 224
    n_splits: int = 5
    folds: tuple[int, ...] = ()
    epochs: int = 10
    batch_size: int = 32
    lr: float = 1e-3
    weight_decay: float = 1e-4
    label_smoothing: float = 0.1
    mixup_alpha: float = 0.2
    cutmix_alpha: float = 1.0
    mix_prob: float = 0.5
    ema_decay: float = 0.999
    amp: bool = True
    tta: bool = True
    num_workers: int = 0
    seed: int = 42
    output_dir: str = "artifacts"
    root_dir: str = "."

    def __post_init__(self) -> None:
        if self.backend not in BACKENDS:
            raise ConfigError(f"backend {self.backend!r} inconnu ({BACKENDS}).")
        if not 0 <= self.label_smoothing < 1 or not 0 <= self.mix_prob <= 1:
            raise ConfigError("label_smoothing ∈ [0, 1[ et mix_prob ∈ [0, 1] attendus.")
        if any(f < 0 or f >= self.n_splits for f in self.folds):
            raise ConfigError(f"folds {self.folds} hors de [0, {self.n_splits - 1}].")
        if len(set(self.classes)) != len(self.classes) or len(self.classes) < 2:
            raise ConfigError("Au moins deux classes distinctes attendues.")

    @classmethod
    def from_yaml(cls, path: str | Path) -> VisionConfig:
        return dataclass_from_yaml(cls, path)

    def resolve(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else Path(self.root_dir) / p

    @property
    def run_dir(self) -> Path:
        return self.resolve(self.output_dir) / self.name

"""Métadonnées d'images et plis (sans PyTorch).

Règle anti-fuite : toutes les vues d'une même plante (et idéalement d'une même parcelle) restent dans le même pli
(StratifiedGroupKFold). Sans métadonnées, chaque image est son propre groupe — à éviter en conditions réelles,
car les rafales ESP32-CAM d'une même plante sont quasi identiques et gonflent artificiellement le score.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from agriml.cv import assert_no_leakage, stratified_group_splits
from agriml.vision.config import VisionConfig

logger = logging.getLogger(__name__)
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


def scan_folders(data_dir: Path, classes: tuple[str, ...]) -> pd.DataFrame:
    """Repli : arborescence <classe>/<image> ; groupe = nom de fichier (aucune information de plante)."""
    rows = [{"path": p.relative_to(data_dir).as_posix(), "label": label, "plant_id": p.stem}
            for label in classes for p in sorted((data_dir / label).glob("*")) if p.suffix.lower() in IMAGE_SUFFIXES]
    logger.warning("Pas de metadata.csv : groupes = images (risque de fuite entre vues d'une même plante).")
    return pd.DataFrame(rows)


def load_metadata(cfg: VisionConfig) -> pd.DataFrame:
    data_dir = cfg.resolve(cfg.data_dir)
    meta_path = data_dir / cfg.metadata
    meta = pd.read_csv(meta_path) if meta_path.exists() else scan_folders(data_dir, cfg.classes)
    unknown = set(meta[cfg.label_col]) - set(cfg.classes)
    if unknown:
        raise ValueError(f"Étiquettes absentes de la configuration : {sorted(unknown)}")
    missing = [p for p in meta[cfg.path_col] if not (data_dir / p).exists()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} images introuvables (ex. {missing[0]}).")
    return meta.assign(target=meta[cfg.label_col].map({c: i for i, c in enumerate(cfg.classes)}))


def make_folds(meta: pd.DataFrame, cfg: VisionConfig) -> np.ndarray:
    """Numéro de pli par image (StratifiedGroupKFold sur la plante), vérifié sans fuite de groupe."""
    groups = meta[cfg.group_col].to_numpy()
    splits = stratified_group_splits(meta["target"].to_numpy(), groups, cfg.n_splits, cfg.seed)
    assert_no_leakage(splits, len(meta), groups=groups)
    fold = np.full(len(meta), -1, dtype=int)
    for k, (_, va) in enumerate(splits):
        fold[va] = k
    return fold

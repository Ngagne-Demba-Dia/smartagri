"""Jeu de données PyTorch d'images de feuilles (chemins + cibles issus des métadonnées)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset

from agriml.vision.augment import build_transforms
from agriml.vision.config import VisionConfig


class LeafDataset(Dataset):
    def __init__(self, root: Path, paths: list[str], targets: np.ndarray, transform: Callable):
        self.root, self.paths, self.targets, self.transform = Path(root), list(paths), np.asarray(targets), transform

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        with Image.open(self.root / self.paths[idx]) as img:
            x = self.transform(img.convert("RGB"))
        return x, int(self.targets[idx])


def make_loader(cfg: VisionConfig, meta: pd.DataFrame, train: bool) -> DataLoader:
    """`drop_last` à l'entraînement : un dernier lot d'une image casserait BatchNorm et Mixup."""
    ds = LeafDataset(cfg.resolve(cfg.data_dir), meta[cfg.path_col].tolist(), meta["target"].to_numpy(),
                     build_transforms(cfg.image_size, train))
    generator = torch.Generator().manual_seed(cfg.seed)
    return DataLoader(ds, batch_size=cfg.batch_size, shuffle=train, drop_last=train and len(ds) > cfg.batch_size,
                      num_workers=cfg.num_workers, generator=generator, pin_memory=torch.cuda.is_available())

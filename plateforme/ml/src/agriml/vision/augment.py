"""Augmentations et régularisation pour photos de feuilles prises au champ (PyTorch / torchvision v2).

Choix agronomiques : teinte quasi figée (hue ≤ 0,02, la couleur EST le symptôme : jaunissement, nécroses
brunes), éblouissement solaire simulé (SunGlare), flou de mise au point (ESP32-CAM sans autofocus), recadrages
partiels (feuille hors cadre), effacement aléatoire (occlusions). Mixup/CutMix avec cibles douces et
lissage d'étiquettes ; à couper pour les dernières époques si les classes sont très déséquilibrées.
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F  # noqa: N812 (convention PyTorch)
from torchvision.transforms import v2

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class SunGlare(torch.nn.Module):
    """Tache lumineuse gaussienne ajoutée sur un tenseur [C, H, W] dans [0, 1] (soleil rasant, reflets)."""

    def __init__(self, p: float = 0.3, max_strength: float = 0.6):
        super().__init__()
        self.p, self.max_strength = p, max_strength

    def forward(self, img: torch.Tensor) -> torch.Tensor:
        if torch.rand(1).item() >= self.p:
            return img
        _, h, w = img.shape
        cy, cx = torch.rand(2) * torch.tensor([h, w])
        sigma = (0.15 + 0.25 * torch.rand(1)) * min(h, w)
        yy, xx = torch.meshgrid(torch.arange(h), torch.arange(w), indexing="ij")
        blob = torch.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sigma**2))
        return (img + self.max_strength * torch.rand(1) * blob).clamp(0, 1)


def build_transforms(image_size: int, train: bool) -> v2.Compose:
    base = [v2.ToImage(), v2.ToDtype(torch.float32, scale=True)]
    if not train:
        return v2.Compose([*base, v2.Resize((image_size, image_size), antialias=True),
                           v2.Normalize(IMAGENET_MEAN, IMAGENET_STD)])
    return v2.Compose([
        *base,
        v2.RandomResizedCrop(image_size, scale=(0.6, 1.0), antialias=True),
        v2.RandomHorizontalFlip(), v2.RandomVerticalFlip(),
        v2.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.02),
        v2.RandomApply([v2.GaussianBlur(kernel_size=5, sigma=(0.1, 1.5))], p=0.3),
        SunGlare(p=0.3),
        v2.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        v2.RandomErasing(p=0.25, scale=(0.02, 0.15)),
    ])


def soft_targets(y: torch.Tensor, n_classes: int, smoothing: float = 0.0) -> torch.Tensor:
    """One-hot lissé : (1 − ε) sur la vraie classe, ε / K réparti uniformément."""
    one_hot = F.one_hot(y, n_classes).float()
    return one_hot * (1.0 - smoothing) + smoothing / n_classes


def soft_cross_entropy(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    return torch.sum(-targets * F.log_softmax(logits, dim=-1), dim=-1).mean()


def _cutmix_box(h: int, w: int, lam: float, rng: np.random.Generator) -> tuple[int, int, int, int]:
    cut = np.sqrt(1.0 - lam)
    ch, cw = int(h * cut), int(w * cut)
    cy, cx = rng.integers(h), rng.integers(w)
    return max(cy - ch // 2, 0), min(cy + ch // 2, h), max(cx - cw // 2, 0), min(cx + cw // 2, w)


def mix_batch(x: torch.Tensor, targets: torch.Tensor, rng: np.random.Generator, mixup_alpha: float = 0.2,
              cutmix_alpha: float = 1.0, prob: float = 0.5) -> tuple[torch.Tensor, torch.Tensor]:
    """Mixup ou CutMix (tirage 50/50) avec probabilité `prob` ; renvoie de nouveaux tenseurs (pas de mutation)."""
    if rng.random() >= prob or len(x) < 2 or (mixup_alpha <= 0 and cutmix_alpha <= 0):
        return x, targets
    perm = torch.from_numpy(rng.permutation(len(x)))
    use_cutmix = cutmix_alpha > 0 and (mixup_alpha <= 0 or rng.random() < 0.5)
    if not use_cutmix:
        lam = float(rng.beta(mixup_alpha, mixup_alpha))
        return lam * x + (1 - lam) * x[perm], lam * targets + (1 - lam) * targets[perm]
    lam = float(rng.beta(cutmix_alpha, cutmix_alpha))
    y0, y1, x0, x1 = _cutmix_box(x.shape[2], x.shape[3], lam, rng)
    mixed = x.clone()
    mixed[:, :, y0:y1, x0:x1] = x[perm][:, :, y0:y1, x0:x1]
    lam_eff = 1.0 - (y1 - y0) * (x1 - x0) / (x.shape[2] * x.shape[3])
    return mixed, lam_eff * targets + (1 - lam_eff) * targets[perm]

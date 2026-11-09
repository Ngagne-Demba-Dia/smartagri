"""Fabrique de modèles de vision (timm → Hugging Face → torchvision) et moyenne exponentielle des poids (EMA).

- timm (optionnel) : le plus large choix (EfficientNet, ConvNeXt, EfficientViT…), meilleur pour la compétition ;
- HF transformers (optionnel) : ViT / ConvNeXt / Swin pré-entraînés du Hub (`model_name` = identifiant du Hub) ;
- torchvision : toujours disponible ici, MobileNetV3 / EfficientNet / ResNet — suffisant pour l'embarqué.
`pretrained=False` par défaut : aucun téléchargement de poids sans décision explicite.
"""

from __future__ import annotations

import copy
import logging

import torch
from torch import nn

from agriml._optional import install_hint, optional_import
from agriml.vision.config import VisionConfig

logger = logging.getLogger(__name__)


class HFLogits(nn.Module):
    """Adapte un modèle HF (sortie objet `.logits`) à l'interface tenseur → logits."""

    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(pixel_values=x).logits


def _timm_model(cfg: VisionConfig, n_classes: int) -> nn.Module | None:
    timm = optional_import("timm")
    if timm is None:
        if cfg.backend == "timm":
            raise ImportError(f"backend timm demandé mais absent ({install_hint('timm')}).")
        return None
    return timm.create_model(cfg.model_name, pretrained=cfg.pretrained, num_classes=n_classes)


def _hf_model(cfg: VisionConfig, n_classes: int) -> nn.Module:
    transformers = optional_import("transformers")
    if transformers is None:
        raise ImportError(f"backend hf demandé mais absent ({install_hint('transformers')}).")
    if cfg.pretrained:
        model = transformers.AutoModelForImageClassification.from_pretrained(
            cfg.model_name, num_labels=n_classes, ignore_mismatched_sizes=True)
    else:
        conf = transformers.AutoConfig.for_model("vit", image_size=cfg.image_size, num_labels=n_classes,
                                                 hidden_size=192, num_hidden_layers=4, num_attention_heads=3,
                                                 intermediate_size=384, patch_size=16)
        model = transformers.AutoModelForImageClassification.from_config(conf)
    return HFLogits(model)


def _torchvision_model(cfg: VisionConfig, n_classes: int) -> nn.Module:
    import torchvision

    if not cfg.pretrained:
        return torchvision.models.get_model(cfg.model_name, weights=None, num_classes=n_classes)
    model = torchvision.models.get_model(cfg.model_name, weights="DEFAULT")
    _replace_head(model, n_classes)
    return model


def _replace_head(model: nn.Module, n_classes: int) -> None:
    """Remplace la dernière couche linéaire (classifier / fc / heads) par une tête à `n_classes` sorties."""
    for attr in ("classifier", "fc", "heads", "head"):
        head = getattr(model, attr, None)
        if isinstance(head, nn.Linear):
            setattr(model, attr, nn.Linear(head.in_features, n_classes))
            return
        if isinstance(head, nn.Sequential):
            idx = max(i for i, m in enumerate(head) if isinstance(m, nn.Linear))
            head[idx] = nn.Linear(head[idx].in_features, n_classes)
            return
    raise ValueError(f"Tête de classification introuvable pour {type(model).__name__}.")


def create_model(cfg: VisionConfig, n_classes: int) -> tuple[nn.Module, str]:
    """Renvoie (modèle, backend utilisé) selon `cfg.backend` (auto = timm si installé, sinon torchvision)."""
    if cfg.backend == "hf":
        return _hf_model(cfg, n_classes), "hf"
    if cfg.backend in ("auto", "timm"):
        model = _timm_model(cfg, n_classes)
        if model is not None:
            return model, "timm"
        logger.info("timm non installé : repli torchvision (%s).", install_hint("timm"))
    return _torchvision_model(cfg, n_classes), "torchvision"


class ModelEMA:
    """Copie des poids moyennée exponentiellement ; souvent +0,5 à +1 point en fin d'entraînement court."""

    def __init__(self, model: nn.Module, decay: float = 0.999):
        self.decay = decay
        self.updates = 0
        self.module = copy.deepcopy(model).eval()
        for p in self.module.parameters():
            p.requires_grad_(False)

    @property
    def current_decay(self) -> float:
        """Montée progressive (style timm) : un entraînement court n'est pas figé sur les poids initiaux."""
        return min(self.decay, (1 + self.updates) / (10 + self.updates))

    @torch.no_grad()
    def update(self, model: nn.Module) -> None:
        self.updates += 1
        decay = self.current_decay
        current = model.state_dict()
        for name, ema_value in self.module.state_dict().items():
            value = current[name].detach()
            if ema_value.dtype.is_floating_point:
                ema_value.mul_(decay).add_(value, alpha=1.0 - decay)
            else:
                ema_value.copy_(value)

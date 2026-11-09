"""Distillation de connaissances : un grand modèle « professeur » entraîne un petit « élève » déployable.

Trois variantes de déploiement (même jeu d'étiquettes, même filtre de verdict) :

1. ESP32-CAM, sur l'appareil (compromis coût / autonomie) : élève minuscule (MobileNetV3-small 0.35×, 96 px,
   int8 TFLite-Micro, < 300 ko). Ne décide que « suspect / pas suspect » ; il déclenche l'envoi de la photo,
   le diagnostic fin se fait plus haut. Latence ~1 s, fonctionne sans réseau.
2. Passerelle / téléphone, en périphérie (meilleur compromis production) : élève MobileNetV3-large ou
   EfficientNet-B0 à 224 px, ONNX ou TFLite fp16, ~10–30 ms sur CPU ARM ; diagnostic des 3 classes.
3. Serveur (compétition, référence) : professeur (ConvNeXt / EfficientNetV2 / ViT via timm ou HF), TTA,
   ensemble de plis ; sert aussi à pseudo-étiqueter les images non annotées remontées par les caméras.

Perte : α · KL(softmax(z_s/T) ‖ softmax(z_t/T)) · T² + (1 − α) · CE(z_s, y). Le facteur T² garde l'échelle des
gradients indépendante de la température.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F  # noqa: N812
from torch import nn

DEFAULT_TEMPERATURE = 4.0
DEFAULT_ALPHA = 0.7


def distillation_loss(student_logits: torch.Tensor, teacher_logits: torch.Tensor, targets: torch.Tensor,
                      temperature: float = DEFAULT_TEMPERATURE, alpha: float = DEFAULT_ALPHA) -> torch.Tensor:
    """`targets` : indices de classe ou cibles douces (mixup / lissage)."""
    soft_student = F.log_softmax(student_logits / temperature, dim=-1)
    soft_teacher = F.softmax(teacher_logits.detach() / temperature, dim=-1)
    kd = F.kl_div(soft_student, soft_teacher, reduction="batchmean") * temperature**2
    if targets.dtype.is_floating_point:
        ce = torch.sum(-targets * F.log_softmax(student_logits, dim=-1), dim=-1).mean()
    else:
        ce = F.cross_entropy(student_logits, targets)
    return alpha * kd + (1 - alpha) * ce


def distill_step(student: nn.Module, teacher: nn.Module, x: torch.Tensor, targets: torch.Tensor,
                 optimizer: torch.optim.Optimizer, temperature: float = DEFAULT_TEMPERATURE,
                 alpha: float = DEFAULT_ALPHA) -> float:
    """Un pas d'optimisation de l'élève ; le professeur reste figé (eval, sans gradient)."""
    teacher.eval()
    with torch.no_grad():
        teacher_logits = teacher(x)
    student.train()
    loss = distillation_loss(student(x), teacher_logits, targets, temperature, alpha)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    optimizer.step()
    return float(loss.detach())

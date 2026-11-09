"""Export ONNX (axe lot dynamique) et contrôle de parité PyTorch ↔ onnxruntime.

Le modèle exporté sert la passerelle / le serveur (onnxruntime) ; la variante ESP32-CAM passe par une conversion
TFLite-Micro int8 hors de ce module (voir `agriml.vision.distill`). Un écart de parité > 1e-3 sur les logits
bloque la publication : opérateur mal converti ou prétraitement différent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

from agriml._optional import optional_import

logger = logging.getLogger(__name__)
ONNX_OPSET = 17
PARITY_ATOL = 1e-3


@dataclass(frozen=True)
class OnnxExportResult:
    ok: bool
    path: str | None = None
    error: str | None = None
    max_abs_diff: float | None = None
    parity_ok: bool | None = None


def export_onnx(model: nn.Module, path: str | Path, image_size: int) -> OnnxExportResult:
    """Exporte en ONNX (exporteur TorchScript, opset 17) ; toute erreur est capturée et renvoyée."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dummy = torch.randn(1, 3, image_size, image_size)
    try:
        torch.onnx.export(model.eval(), (dummy,), str(path), input_names=["image"], output_names=["logits"],
                          opset_version=ONNX_OPSET, dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
                          dynamo=False)
    except Exception as exc:  # noqa: BLE001 — l'export ne doit jamais faire échouer l'entraînement
        logger.warning("Export ONNX impossible : %s: %s", type(exc).__name__, exc)
        return OnnxExportResult(False, None, f"{type(exc).__name__}: {exc}")
    return OnnxExportResult(True, str(path))


def check_parity(model: nn.Module, onnx_path: str | Path, image_size: int, batch: int = 4,
                 seed: int = 0) -> tuple[float, bool]:
    """Écart max des logits PyTorch vs onnxruntime sur un lot aléatoire (lot ≠ 1 : vérifie l'axe dynamique)."""
    ort = optional_import("onnxruntime")
    if ort is None:
        raise ImportError("onnxruntime absent : parité non vérifiable.")
    x = torch.randn(batch, 3, image_size, image_size, generator=torch.Generator().manual_seed(seed))
    with torch.no_grad():
        ref = model.eval()(x).numpy()
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    out = session.run(None, {session.get_inputs()[0].name: x.numpy()})[0]
    diff = float(np.max(np.abs(ref - out)))
    return diff, diff <= PARITY_ATOL


def export_and_check(model: nn.Module, path: str | Path, image_size: int) -> OnnxExportResult:
    result = export_onnx(model, path, image_size)
    if not result.ok:
        return result
    try:
        diff, ok = check_parity(model, path, image_size)
    except Exception as exc:  # noqa: BLE001
        return OnnxExportResult(True, result.path, f"parité non vérifiée : {type(exc).__name__}: {exc}")
    logger.info("Parité ONNX : écart max %.2e (%s)", diff, "OK" if ok else "ÉCHEC")
    return OnnxExportResult(True, result.path, None, diff, ok)

"""DiseaseDetectionService (B4) — classification maladies foliaires (Riz) sur MobileNetV3."""

import io
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .security import MAX_IMAGE_BYTES, ensure_within_root, validate_safe_image_path
from .types import ConfidenceLevel, ServiceResponse, confidence_level


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISEASE_DIR = ROOT / "models" / "disease"


class DiseaseDetectionService:
    """B4 — Détection des maladies foliaires du riz (Healthy, Leaf_Blast, Neck_Blast, Brown_Spot)."""

    RECOMMENDATIONS = {
        "Rice___Healthy": "Feuillage sain. Maintenir le suivi hydrique normal.",
        "Rice___Leaf_Blast": "Pyriculariose foliaire détectée. Éviter excès d'azote, inspecter la parcelle et consulter un conseiller phytosanitaire.",
        "Rice___Neck_Blast": "Pyriculariose du col détectée (risque perte rendement). Intervention phytosanitaire rapide recommandée.",
        "Rice___Brown_Spot": "Helminthosporiose (taches brunes) détectée. Vérifier carences potassium/silice et drainage.",
    }

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = Path(models_dir) if models_dir else DEFAULT_DISEASE_DIR
        self.head_path = self.models_dir / "b4_rice_head.pt"
        self.meta_path = self.models_dir / "b4_rice_metadata.json"
        self.backbone = None
        self.head = None
        self.tfm = None
        self.meta: Dict[str, Any] = {}
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.head_path.exists() or not self.meta_path.exists():
            self.load_error = f"Modèle B4 absent dans {self.models_dir}"
            return
        try:
            import torch
            import torch.nn as nn
            from torchvision import models, transforms

            self.meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
            weights = models.MobileNet_V3_Small_Weights.DEFAULT
            backbone = models.mobilenet_v3_small(weights=weights)
            backbone.classifier = nn.Identity()
            backbone.eval()
            self.backbone = backbone

            head = nn.Sequential(
                nn.Linear(self.meta["in_dim"], 128),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(128, len(self.meta["classes"])),
            )
            safe_head = ensure_within_root(self.head_path, [self.models_dir])
            try:
                state_dict = torch.load(safe_head, map_location="cpu", weights_only=True)
            except TypeError:
                state_dict = torch.load(safe_head, map_location="cpu")
            head.load_state_dict(state_dict)
            head.eval()
            self.head = head

            self.tfm = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        except Exception as exc:
            self.load_error = f"Erreur chargement B4: {exc}"

    @property
    def is_ready(self) -> bool:
        return self.backbone is not None and self.head is not None and self.load_error is None

    def _infer_pil(self, im: Any, t0: float) -> ServiceResponse:
        import torch

        x = self.tfm(im.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            logits = self.head(self.backbone(x))
            probs = torch.softmax(logits, dim=1)[0].numpy()

        top_idx = int(probs.argmax())
        label = self.meta["classes"][top_idx]
        conf = round(float(probs[top_idx]), 4)
        return ServiceResponse(
            service="disease_detection",
            values={
                "predicted_class": label,
                "probabilities": {c: round(float(probs[i]), 4) for i, c in enumerate(self.meta["classes"])},
                "recommendation": self.RECOMMENDATIONS.get(label, "Vérification terrain recommandée."),
            },
            confidence=conf,
            confidence_level=confidence_level(conf),
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )

    def predict_image_bytes(self, image_bytes: bytes) -> ServiceResponse:
        """Inférence sécurisée directement depuis des octets image (sans accès au système de fichiers)."""
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse(
                "disease_detection", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=self.load_error or "Non chargé",
            )
        if not image_bytes or len(image_bytes) > MAX_IMAGE_BYTES:
            return ServiceResponse(
                "disease_detection", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason="Image vide ou trop volumineuse.",
            )
        from PIL import Image, UnidentifiedImageError

        try:
            with Image.open(io.BytesIO(image_bytes)) as im:
                return self._infer_pil(im, t0)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            return ServiceResponse(
                "disease_detection", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=f"Image invalide: {exc}",
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

    def predict_image(self, image_path: Path, allowed_roots: Optional[Iterable[Path]] = None) -> ServiceResponse:
        t0 = time.perf_counter()
        if not self.is_ready:
            return ServiceResponse("disease_detection", {}, 0.0, ConfidenceLevel.UNRELIABLE, abstained=True, abstention_reason=self.load_error or "Non chargé")
        try:
            safe_path = validate_safe_image_path(Path(image_path), allowed_roots=allowed_roots)
        except (FileNotFoundError, ValueError, OSError) as exc:
            return ServiceResponse(
                "disease_detection", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=f"Image refusée ou introuvable: {exc}",
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

        from PIL import Image, UnidentifiedImageError

        try:
            with Image.open(safe_path) as im:
                return self._infer_pil(im, t0)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            return ServiceResponse(
                "disease_detection", {}, 0.0, ConfidenceLevel.UNRELIABLE,
                abstained=True, abstention_reason=f"Image invalide: {exc}",
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            )

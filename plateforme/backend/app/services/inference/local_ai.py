"""Client HTTP vers le runtime IA local `smartagri-ai` (port 8001)."""

from __future__ import annotations

import base64
import logging
from collections.abc import Mapping
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SmartAgriAIClient:
    """Pont optionnel Backend → `smartagri-ai/api/app.py` avec pool HTTP et authentification inter-services."""

    def __init__(
        self,
        base_url: str,
        timeout_s: float = 5.0,
        client: httpx.Client | None = None,
        api_key: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.api_key = api_key.strip()
        self._owns_client = client is None and bool(self.base_url)
        self._client = client or (
            httpx.Client(
                timeout=self.timeout_s,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                follow_redirects=False,
            )
            if self.base_url
            else None
        )

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _post(
        self,
        path: str,
        payload: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not self.enabled or self._client is None:
            return None
        try:
            resp = self._client.post(
                f"{self.base_url}{path}",
                json=dict(payload) if payload is not None else {},
                params=dict(params) if params else None,
                headers=self._headers(),
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else None
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("smartagri-ai indisponible sur %s (%s) : %s", path, self.base_url, exc)
            return None

    def _get(self, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
        if not self.enabled or self._client is None:
            return None
        try:
            resp = self._client.get(
                f"{self.base_url}{path}",
                params=dict(params) if params else None,
                headers=self._headers(),
                timeout=self.timeout_s,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else None
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("smartagri-ai GET %s échoué (%s) : %s", path, self.base_url, exc)
            return None

    def health(self) -> dict[str, Any] | None:
        return self._get("/health")

    def predict_soil(self, features: Mapping[str, float]) -> dict[str, Any] | None:
        return self._post("/soil/predict", {"features": dict(features)})

    def predict_rain(self, features: Mapping[str, float]) -> dict[str, Any] | None:
        return self._post("/rain/predict", {"features": dict(features)})

    def predict_et0(self, features: Mapping[str, float]) -> dict[str, Any] | None:
        return self._post("/et0/predict", {"features": dict(features)})

    def detect_anomaly(self, features: Mapping[str, Any], crop: str = "oignon") -> dict[str, Any] | None:
        return self._post("/anomaly/detect", {"features": dict(features), "crop": crop})

    def ask_orchestrator(
        self, query: str, features: Mapping[str, Any] | None = None, crop: str = "oignon"
    ) -> dict[str, Any] | None:
        return self._post("/orchestrator/ask", {"query": query, "features": dict(features or {}), "crop": crop})

    def predict_yield(
        self, crop: str = "Millet", region: str = "Kaolack", year: int = 2025, area_ha: float = 1000.0
    ) -> dict[str, Any] | None:
        return self._post("/yield/predict", {}, params={"crop": crop, "region": region, "year": year, "area_ha": area_ha})

    def predict_price(
        self, commodity: str = "Onions", market: str = "Tilene", region: str = "Dakar", year: int = 2026, month: int = 11
    ) -> dict[str, Any] | None:
        return self._post(
            "/price/predict",
            {},
            params={"commodity": commodity, "market": market, "region": region, "year": year, "month": month},
        )

    def market_clusters(self, top_n: int = 5) -> dict[str, Any] | None:
        return self._get("/market/clusters", params={"top_n": top_n})

    def predict_disease_bytes(self, image_base64: str, content_type: str = "image/jpeg") -> dict[str, Any] | None:
        return self._post("/disease/predict-bytes", {"image_base64": image_base64, "content_type": content_type})

    def interpret_wolof(self, text: str) -> dict[str, Any] | None:
        return self._post("/voice/intent", {"text": text})

    def search_knowledge(self, query: str, top_k: int = 3) -> dict[str, Any] | None:
        return self._post("/knowledge/search", {"query": query, "top_k": top_k})

    def transcribe_voice(
        self, audio_base64: str, content_type: str = "audio/wav", duration_s: float = 1.0, language_hint: str = "wo"
    ) -> dict[str, Any] | None:
        return self._post(
            "/voice/transcribe",
            {
                "audio_base64": audio_base64,
                "content_type": content_type,
                "duration_s": duration_s,
                "language_hint": language_hint,
            },
        )


class SmartAgriAITranscriber:
    """Adaptateur `Transcriber` délégant l'ASR Wolof/Français au runtime `smartagri-ai`."""

    def __init__(self, client: SmartAgriAIClient) -> None:
        self._client = client

    def transcribe(
        self, audio_bytes: bytes, content_type: str, duration_s: float, language_hint: str | None
    ) -> Any:
        from app.core.errors import AppError
        from app.services.assistant.transcribe import TranscribeOutput

        b64 = base64.b64encode(audio_bytes).decode("ascii")
        res = self._client.transcribe_voice(
            audio_base64=b64,
            content_type=content_type,
            duration_s=duration_s,
            language_hint=language_hint or "wo",
        )
        if not res or res.get("abstained"):
            raise AppError("MODEL_UNAVAILABLE", "Service ASR Wolof indisponible sur smartagri-ai.", 503)
        return TranscribeOutput(
            text=str(res.get("text", "")),
            language=str(res.get("language", language_hint or "wo")),
            confidence_score=float(res.get("confidence", 0.85)),
            model_version=str(res.get("model_version", "whisper-small-wolof")),
            source="smartagri-ai",
            calibrated=False,
        )


class SmartAgriAIVisionAnalyzer:
    """Adaptateur `VisionAnalyzer` délégant B4 (maladies foliaires) à `smartagri-ai` via octets base64."""

    def __init__(self, client: SmartAgriAIClient) -> None:
        self._client = client

    def analyze(self, image_bytes: bytes, content_type: str) -> Any:
        from app.core.errors import AppError
        from app.services.diagnoses import VisionCandidate, VisionPrediction

        b64 = base64.b64encode(image_bytes).decode("ascii")
        res = self._client.predict_disease_bytes(b64, content_type=content_type)
        if not res or res.get("abstained"):
            raise AppError("MODEL_UNAVAILABLE", "Diagnostic visuel indisponible sur smartagri-ai.", 503)
        values = res.get("values", {})
        probs: Mapping[str, Any] = values.get("probabilities", {})
        ranked = sorted(probs.items(), key=lambda item: float(item[1]), reverse=True)[:3]
        top3 = [VisionCandidate(code=str(code), probability=float(prob)) for code, prob in ranked]
        predicted = str(values.get("predicted_class", ""))
        label = "healthy" if "healthy" in predicted.lower() else ("sick" if top3 else "suspect")
        return VisionPrediction(
            label=label,
            top3=top3,
            model_version="b4-mobilenetv3-rice",
            source="agriml",
            calibrated=False,
        )

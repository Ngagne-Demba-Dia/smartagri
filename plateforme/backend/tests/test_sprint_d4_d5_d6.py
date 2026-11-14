"""Tests Sprint D4, D5 et D6 : fertilization, pest_risk, diagnoses/analyze et assistant/transcribe."""

from __future__ import annotations

import base64
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.services.assistant.transcribe import TranscribeOutput
from app.services.diagnoses import VisionCandidate, VisionPrediction
from app.services.pest_risk import PestRule
from tests.conftest import NOW, World, point


def test_d4_fertilization_and_pest_risk_default_and_injected(client: TestClient, app: Any, world: World) -> None:
    """Par défaut (sans barème ISRA/DPV validé), pas de dose NPK ni d'alerte ravageur inventée ; injectable sinon."""
    cyc = client.post(
        f"/v1/fields/{world.field_id}/crop-cycles",
        headers=world.admin_a,
        json={"crop": "onion", "variety": "Violet de Galmi", "planted_on": "2026-10-01"},
    )
    assert cyc.status_code == 201, cyc.text

    pts = [
        point(
            ts=NOW - timedelta(minutes=15),
            soil_moisture_pct=35.0,
            air_temp_c=29.0,
            n_mgkg=12,
            p_mgkg=18,
            k_mgkg=170,
        )
    ]
    client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key}, json={"points": pts})

    # 1. Mode par défaut sans référentiel injecté
    fert_res = client.get(f"/v1/fields/{world.field_id}/fertilization", headers=world.farmer_a)
    assert fert_res.status_code == 200, fert_res.text
    fert = fert_res.json()["data"]
    assert fert["field_id"] == str(world.field_id)
    assert fert["crop"] == "onion"
    assert fert["n_kg_ha"] is None and fert["p_kg_ha"] is None and fert["k_kg_ha"] is None
    assert fert["npk_class"] == "bas"
    assert fert["indicative"] is True
    assert fert["provenance"]["model_name"] == "fert_reco"
    assert fert["provenance"]["source"] == "rules"

    pest_res = client.get(f"/v1/fields/{world.field_id}/pest-risk", headers=world.farmer_a)
    assert pest_res.status_code == 200, pest_res.text
    pest = pest_res.json()["data"]
    assert pest["field_id"] == str(world.field_id)
    assert pest["pests"] == []
    assert pest["provenance"]["model_name"] == "risk_rules"
    assert pest["provenance"]["source"] == "rules"

    # 2. Avec barème ISRA et règles DPV injectés sur app.state
    app.state.fertilization_reference = {"onion": {"n": 120, "p": 60, "k": 120}}
    app.state.pest_reference = {
        "onion": [PestRule(pest_code="thrips_tabaci", min_temp_c=20.0, max_temp_c=38.0, min_rain_mm=0.0)]
    }
    try:
        fert2 = client.get(f"/v1/fields/{world.field_id}/fertilization", headers=world.farmer_a).json()["data"]
        assert (fert2["n_kg_ha"], fert2["p_kg_ha"], fert2["k_kg_ha"]) == (144, 72, 144)

        pest2 = client.get(f"/v1/fields/{world.field_id}/pest-risk", headers=world.farmer_a).json()["data"]
        assert len(pest2["pests"]) == 1
        assert pest2["pests"][0]["pest_code"] == "thrips_tabaci"
        assert pest2["pests"][0]["p_outbreak_7d"] is None
    finally:
        app.state.fertilization_reference = None
        app.state.pest_reference = None


def test_d5_diagnosis_analyze_validation_503_and_abstention(client: TestClient, app: Any, world: World) -> None:
    """`POST /v1/diagnoses/analyze` vérifie taille (413), périmètre (404), 503 sans bundle et abstention < 0.7."""
    small_img = base64.b64encode(b"\xff\xd8\xff\xe0fake-jpeg-bytes").decode("ascii")
    payload = {
        "image_base64": small_img,
        "content_type": "image/jpeg",
        "field_id": str(world.field_id),
        "device_id": None,
        "captured_at": NOW.isoformat(),
    }

    # 1. Sans analyseur chargé -> 503 MODEL_UNAVAILABLE honnête
    res_503 = client.post("/v1/diagnoses/analyze", headers=world.farmer_a, json=payload)
    assert res_503.status_code == 503
    assert res_503.json()["error"]["code"] == "MODEL_UNAVAILABLE"

    # 2. Image > 256 Kio -> 413 PAYLOAD_TOO_LARGE
    huge_img = base64.b64encode(b"x" * (210 * 1024)).decode("ascii")
    res_413 = client.post(
        "/v1/diagnoses/analyze",
        headers=world.farmer_a,
        json={**payload, "image_base64": huge_img},
    )
    assert res_413.status_code == 413
    assert res_413.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"

    # 3. Hors périmètre multi-organisation -> 404 NOT_FOUND
    res_404 = client.post("/v1/diagnoses/analyze", headers=world.admin_b, json=payload)
    assert res_404.status_code == 404

    # 4. Avec analyseur injecté : cas nominal (confiance >= 0.7) et cas d'abstention (< 0.7)
    class FakeAnalyzer:
        def __init__(self, prob: float) -> None:
            self.prob = prob

        def analyze(self, image_bytes: bytes, content_type: str) -> VisionPrediction:
            return VisionPrediction(
                label="sick",
                top3=[
                    VisionCandidate("alternaria_porri", self.prob),
                    VisionCandidate("stemphylium_vesicarium", round(1.0 - self.prob, 2)),
                ],
                model_version="1.2.0",
                source="agriml",
                calibrated=True,
            )

    app.state.vision_analyzer = FakeAnalyzer(0.84)
    try:
        ok_res = client.post("/v1/diagnoses/analyze", headers=world.farmer_a, json=payload)
        assert ok_res.status_code == 200, ok_res.text
        diag = ok_res.json()["data"]
        assert diag["id"] is None
        assert diag["label"] == "sick"
        assert diag["disease_code"] == "alternaria_porri"
        assert diag["abstained"] is False
        assert diag["provenance"]["model_name"] == "vis_disease"
        assert diag["provenance"]["confidence"]["kind"] == "class_probability"
        assert diag["provenance"]["confidence"]["value"] == 0.84

        app.state.vision_analyzer = FakeAnalyzer(0.52)
        abs_res = client.post("/v1/diagnoses/analyze", headers=world.farmer_a, json=payload)
        assert abs_res.status_code == 200
        abs_diag = abs_res.json()["data"]
        assert abs_diag["abstained"] is True
        assert abs_diag["label"] == "suspect"
        assert abs_diag["disease_code"] is None
    finally:
        app.state.vision_analyzer = None


def test_d6_assistant_transcribe_validation_503_and_injected(client: TestClient, app: Any, world: World) -> None:
    """`POST /v1/assistant/transcribe` valide durée/taille/langue, renvoie 503 par défaut et transcrit si injecté."""
    small_audio = base64.b64encode(b"OggS-fake-opus-audio").decode("ascii")
    payload = {
        "audio_base64": small_audio,
        "content_type": "audio/webm;codecs=opus",
        "duration_s": 8.5,
        "language_hint": "wo",
    }

    # 1. Sans fournisseur ASR configuré -> 503 MODEL_UNAVAILABLE
    res_503 = client.post("/v1/assistant/transcribe", headers=world.farmer_a, json=payload)
    assert res_503.status_code == 503
    assert res_503.json()["error"]["code"] == "MODEL_UNAVAILABLE"

    # 2. Durée > 60 s -> 422 VALIDATION_ERROR
    res_422 = client.post(
        "/v1/assistant/transcribe",
        headers=world.farmer_a,
        json={**payload, "duration_s": 75.0},
    )
    assert res_422.status_code == 422

    # 3. Audio > 256 Kio -> 413 PAYLOAD_TOO_LARGE
    huge_audio = base64.b64encode(b"a" * (210 * 1024)).decode("ascii")
    res_413 = client.post(
        "/v1/assistant/transcribe",
        headers=world.farmer_a,
        json={**payload, "audio_base64": huge_audio},
    )
    assert res_413.status_code == 413

    # 4. Avec Transcriber injecté
    class FakeTranscriber:
        def transcribe(
            self, audio_bytes: bytes, content_type: str, duration_s: float, language_hint: str | None
        ) -> TranscribeOutput:
            return TranscribeOutput(
                text="Naka suuf si tay ?",
                language=language_hint or "wo",
                confidence_score=0.88,
                model_version="xlsr-300m-v1",
                source="agriml",
                calibrated=False,
            )

    app.state.transcriber = FakeTranscriber()
    try:
        ok_res = client.post("/v1/assistant/transcribe", headers=world.farmer_a, json=payload)
        assert ok_res.status_code == 200, ok_res.text
        tr = ok_res.json()["data"]
        assert tr["text"] == "Naka suuf si tay ?"
        assert tr["language"] == "wo"
        assert tr["duration_s"] == 8.5
        assert tr["provenance"]["model_name"] == "asst_asr"
        assert tr["provenance"]["confidence"]["kind"] == "probability"
    finally:
        app.state.transcriber = None

"""Tests du pont Backend → runtime IA local `smartagri-ai`."""

from __future__ import annotations

import json

import httpx

from app.core.config import load_settings
from app.services.inference.local_ai import SmartAgriAIClient


def test_smartagri_ai_client_disabled_by_default() -> None:
    settings = load_settings({})
    assert settings.smartagri_ai_url == ""
    cli = SmartAgriAIClient(settings.smartagri_ai_url, settings.smartagri_ai_timeout_s)
    assert not cli.enabled
    assert cli.health() is None
    assert cli.predict_soil({"t_mean_c": 28.0}) is None


def test_smartagri_ai_client_mock_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "soil_nowcast_ready": True})
        if request.url.path == "/soil/predict":
            body = json.loads(request.content)
            assert body["features"]["t_mean_c"] == 28.2
            return httpx.Response(
                200,
                json={"service": "soil_nowcast", "values": {"y_plus_1d": 41.2}, "confidence": 0.8353, "abstained": False},
            )
        if request.url.path == "/orchestrator/ask":
            return httpx.Response(200, json={"intent": "irrigation", "answer": "OK", "confidence": 0.85})
        return httpx.Response(404)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    cli = SmartAgriAIClient("http://smartagri-ai.local:8001", client=http)
    assert cli.enabled
    assert cli.health()["status"] == "ok"
    soil = cli.predict_soil({"t_mean_c": 28.2})
    assert soil is not None and soil["values"]["y_plus_1d"] == 41.2
    orch = cli.ask_orchestrator("Dois-je irriguer ?", {"t_mean_c": 28.2}, crop="oignon")
    assert orch is not None and orch["intent"] == "irrigation"


def test_smartagri_ai_client_graceful_fallback_on_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    cli = SmartAgriAIClient("http://127.0.0.1:9999", client=http)
    assert cli.health() is None
    assert cli.predict_rain({"t_mean_c": 28.2}) is None


def test_smartagri_ai_client_api_key_params_and_vision_adapter() -> None:
    from app.services.inference.local_ai import SmartAgriAIVisionAnalyzer

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        assert request.headers.get("X-API-Key") == "secret-key-123"
        if request.url.path == "/yield/predict":
            assert request.url.params["crop"] == "Millet&evil=1"
            return httpx.Response(200, json={"service": "yield_forecast", "values": {"yield_t_ha": 1.2}, "abstained": False})
        if request.url.path == "/disease/predict-bytes":
            body = json.loads(request.content)
            assert body["image_base64"]
            return httpx.Response(
                200,
                json={
                    "service": "disease_detection",
                    "values": {
                        "predicted_class": "Rice___Leaf_Blast",
                        "probabilities": {"Rice___Leaf_Blast": 0.91, "Rice___Healthy": 0.09},
                    },
                    "abstained": False,
                },
            )
        return httpx.Response(404)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    cli = SmartAgriAIClient("http://smartagri-ai.local:8001", client=http, api_key="secret-key-123")
    y = cli.predict_yield(crop="Millet&evil=1", region="Kaolack")
    assert y is not None and y["values"]["yield_t_ha"] == 1.2

    analyzer = SmartAgriAIVisionAnalyzer(cli)
    pred = analyzer.analyze(b"\xff\xd8\xff\xe0fakejpeg", "image/jpeg")
    assert pred.label == "sick"
    assert pred.top3[0].code == "Rice___Leaf_Blast"
    assert len(captured) == 2


def test_demo_slugs_disabled_in_strict_mode() -> None:
    import pytest
    from app.core.errors import AppError
    from app.services import access

    try:
        access.set_demo_slugs_enabled(False)
        with pytest.raises(AppError) as exc:
            access.parse_uuid("fld-mboro-1", "Parcelle")
        assert exc.value.status == 404
    finally:
        access.set_demo_slugs_enabled(True)

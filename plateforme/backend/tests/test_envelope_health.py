"""Enveloppe d'erreur, en-têtes, limites (413/429), sondes et validation stricte de la configuration."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigError, load_settings
from app.core.metrics import metrics_available
from app.main import MAX_BODY_BYTES, create_app
from tests.conftest import TEST_ENV, World, make_settings

STRICT_ENV = {"APP_ENV": "prod", "DATABASE_URL": "postgresql+psycopg://app@db/agri", "JWT_SECRET": "j" * 48,
              "DEVICE_KEY_PEPPER": "p" * 48, "OCTOPUS_BASE_URL": "https://octopus.example"}


def error_of(response: Any) -> dict[str, Any]:
    body = response.json()
    assert body["success"] is False and body["data"] is None
    return body["error"]


def test_health_and_readiness(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"success": True, "data": {"status": "ok"}, "error": None, "meta": None}
    ready = client.get("/readyz")
    assert ready.status_code == 200 and ready.json()["data"] == {"status": "ready", "database": "ok"}


def test_metrics_endpoint(client: TestClient) -> None:
    response = client.get("/metrics")
    assert response.status_code == (200 if metrics_available() else 404)


def test_unknown_route_is_french_404_envelope(client: TestClient) -> None:
    response = client.get("/v1/inexistant")
    assert response.status_code == 404
    assert error_of(response) == {"code": "NOT_FOUND", "message": "Ressource introuvable."}


def test_missing_token_is_401_with_bearer_challenge(client: TestClient) -> None:
    response = client.get("/v1/farms")
    assert response.status_code == 401 and response.headers["WWW-Authenticate"] == "Bearer"
    assert error_of(response)["code"] == "UNAUTHENTICATED"


def test_validation_error_is_422_envelope(client: TestClient, world: World) -> None:
    response = client.post("/v1/farms", headers=world.admin_a, json={"name": ""})
    assert response.status_code == 422 and error_of(response)["code"] == "VALIDATION_ERROR"


def test_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "abc123def456"})
    assert response.headers["X-Request-ID"] == "abc123def456"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_oversized_body_is_413(client: TestClient) -> None:
    response = client.post("/v1/telemetry/batch", content=b"x" * (MAX_BODY_BYTES + 1),
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 413 and error_of(response)["code"] == "PAYLOAD_TOO_LARGE"


@pytest.mark.parametrize(("path", "body"), [
    ("/v1/auth/token", {"username": "a@b.test", "password": "x" * 12}),
    ("/v1/auth/logout", {"refresh_token": "x" * 40}),
])
def test_auth_endpoints_are_rate_limited(path: str, body: dict[str, str]) -> None:
    """Un compteur par règle : le 3e appel au même point d'entrée est refusé (429 + Retry-After)."""
    app = create_app(make_settings(RATE_LIMIT_AUTH_PER_MIN="2"))
    with TestClient(app) as client:
        responses = [client.post(path, json=body) for _ in range(3)]
        assert [item.status_code for item in responses] == [401, 401, 429]
        assert "Retry-After" in responses[2].headers and error_of(responses[2])["code"] == "RATE_LIMITED"


def test_strict_environment_accepts_complete_configuration() -> None:
    settings = load_settings(STRICT_ENV)
    assert settings.is_strict and settings.auto_create_schema is False


@pytest.mark.parametrize("override", [
    {"DATABASE_URL": ""},
    {"DATABASE_URL": "sqlite:///agri.db"},
    {"JWT_SECRET": "court"},
    {"DEVICE_KEY_PEPPER": ""},
    {"OCTOPUS_BASE_URL": "http://octopus.example"},
    {"ASSISTANT_EFFORT": "max"},
    {"INFERENCE_BACKEND": "gpu"},
    {"APP_ENV": "preprod"},
])
def test_strict_environment_rejects_unsafe_configuration(override: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        load_settings({**STRICT_ENV, **override})


def test_development_fills_missing_secrets() -> None:
    settings = load_settings({**TEST_ENV, "JWT_SECRET": "", "DEVICE_KEY_PEPPER": ""})
    assert len(settings.jwt_secret) >= 32 and settings.device_key_pepper

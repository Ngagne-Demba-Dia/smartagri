"""Authentification : connexion, rotation des jetons de rafraîchissement, réutilisation, 401."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import PASSWORD, World


def _tokens(client: TestClient, email: str) -> dict:
    response = client.post("/v1/auth/token", json={"username": email, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["data"]


def test_login_returns_token_pair_in_envelope(client: TestClient, world: World) -> None:
    body = client.post("/v1/auth/token", json={"username": "ADMIN@a.test", "password": PASSWORD}).json()
    assert body["success"] is True and body["error"] is None
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["expires_in"] > 0


def test_login_wrong_password_is_401_without_detail(client: TestClient, world: World) -> None:
    response = client.post("/v1/auth/token", json={"username": "admin@a.test", "password": "faux"})
    unknown = client.post("/v1/auth/token", json={"username": "absent@a.test", "password": "faux"})
    assert response.status_code == unknown.status_code == 401
    assert response.json()["error"]["code"] == unknown.json()["error"]["code"]


def test_me_requires_bearer_token(client: TestClient, world: World) -> None:
    assert client.get("/v1/me").status_code == 401
    bad = client.get("/v1/me", headers={"Authorization": "Bearer pas-un-jwt"})
    assert bad.status_code == 401 and bad.json()["success"] is False
    me = client.get("/v1/me", headers=world.admin_a).json()["data"]
    assert me["full_name"] == "admin"


def test_refresh_rotates_and_reuse_revokes_family(client: TestClient, world: World) -> None:
    first = _tokens(client, "farmer@a.test")
    rotated = client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200
    second = rotated.json()["data"]
    assert second["refresh_token"] != first["refresh_token"]

    reuse = client.post("/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reuse.status_code == 401
    # La réutilisation révoque toute la famille, y compris le jeton légitime le plus récent.
    after = client.post("/v1/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert after.status_code == 401


def test_access_token_is_not_accepted_as_refresh_token(client: TestClient, world: World) -> None:
    tokens = _tokens(client, "farmer@a.test")
    response = client.post("/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


def test_logout_revokes_refresh_token_and_is_idempotent(client: TestClient, world: World) -> None:
    tokens = _tokens(client, "farmer@a.test")
    first = client.post("/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    again = client.post("/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == again.status_code == 200
    assert first.json()["data"] == {"logged_out": True}
    refused = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refused.status_code == 401


def test_logout_revokes_rotated_descendants(client: TestClient, world: World) -> None:
    original = _tokens(client, "farmer@a.test")
    rotated = client.post("/v1/auth/refresh", json={"refresh_token": original["refresh_token"]}).json()["data"]
    assert client.post("/v1/auth/logout", json={"refresh_token": rotated["refresh_token"]}).status_code == 200
    assert client.post("/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}).status_code == 401


def test_logout_rejects_forged_token(client: TestClient, world: World) -> None:
    response = client.post("/v1/auth/logout", json={"refresh_token": "x" * 40})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID"

"""Kits et seuils d'irrigation (règle firmware v1.1 : 0 ≤ start, start + 5 ≤ stop ≤ 100, entiers)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.agronomy import ThresholdError, thresholds_valid, validate_thresholds
from tests.conftest import SERIAL_A, SERIAL_B, World


@pytest.mark.parametrize(("start", "stop"), [(0, 5), (95, 100), (30, 60), ("30", "60")])
def test_valid_thresholds_are_accepted(start: object, stop: object) -> None:
    assert validate_thresholds(start, stop) == (int(start), int(stop))


@pytest.mark.parametrize(("start", "stop"), [
    (96, 100), (-1, 50), (30, 34), (30, 101), (30.0, 60), (30.5, 60), (True, 60), ("abc", 60), (None, 60),
    ("-1", 60), (30, "60.0"),
])
def test_invalid_thresholds_are_rejected(start: object, stop: object) -> None:
    with pytest.raises(ThresholdError):
        validate_thresholds(start, stop)


def test_threshold_rule_boundaries() -> None:
    assert thresholds_valid(0, 5) and thresholds_valid(95, 100)
    assert not thresholds_valid(96, 100) and not thresholds_valid(0, 4)


def test_put_thresholds_creates_pending_command(client: TestClient, world: World) -> None:
    response = client.put(f"/v1/devices/{world.device_id}/thresholds", headers=world.farmer_a,
                          json={"start": 0, "stop": 5})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["desired"] == {"start_pct": 0, "stop_pct": 5}
    assert data["sync_status"] == "pending" and data["command_id"]
    again = client.get(f"/v1/devices/{SERIAL_A}/thresholds", headers=world.agronomist_a).json()["data"]
    assert again["command_id"] == data["command_id"]


@pytest.mark.parametrize("body", [
    {"start": 96, "stop": 100}, {"start": -1, "stop": 50}, {"start": 30.5, "stop": 60}, {"start": "x", "stop": 60},
    {"start": 30}, {"start": True, "stop": 60},
])
def test_put_invalid_thresholds_is_400(client: TestClient, world: World, body: dict) -> None:
    response = client.put(f"/v1/devices/{world.device_id}/thresholds", headers=world.farmer_a, json=body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "THRESHOLDS_INVALID"


def test_agronomist_cannot_set_thresholds(client: TestClient, world: World) -> None:
    response = client.put(f"/v1/devices/{world.device_id}/thresholds", headers=world.agronomist_a,
                          json={"start": 30, "stop": 60})
    assert response.status_code == 403


def test_device_registration_returns_key_once(client: TestClient, world: World) -> None:
    created = client.post("/v1/devices", headers=world.admin_a, json={"serial": SERIAL_B})
    assert created.status_code == 201
    assert len(created.json()["data"]["device_key"]) >= 32
    listed = client.get("/v1/devices", headers=world.admin_a).json()
    assert listed["meta"]["total"] == 2
    assert all("device_key" not in item and "key_hash" not in item for item in listed["data"])
    duplicate = client.post("/v1/devices", headers=world.admin_a, json={"serial": SERIAL_B})
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "DEVICE_EXISTS"


def test_farmer_cannot_register_device(client: TestClient, world: World) -> None:
    response = client.post("/v1/devices", headers=world.farmer_a, json={"serial": SERIAL_B})
    assert response.status_code == 403


def test_device_detail_by_serial_and_bad_serial(client: TestClient, world: World) -> None:
    detail = client.get(f"/v1/devices/{SERIAL_A}", headers=world.farmer_a)
    assert detail.status_code == 200 and detail.json()["data"]["latest_measurement"] is None
    assert client.post("/v1/devices", headers=world.admin_a, json={"serial": "SA92-12"}).status_code == 422

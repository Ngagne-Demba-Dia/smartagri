"""Ingestion telemetry.v1 : correspondance des clés, plausibilité, idempotence, taille de lot, clé de kit."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Device, Measurement
from app.services.telemetry import clean_metrics, map_kit_payload
from tests.conftest import NOW, SERIAL_A, SERIAL_B, World, point

KIT = {"sol": 41.5, "temp": 31.2, "hum": 55, "pres": 1009.8, "n": 25, "p": 12, "k": 110, "pompe": True,
       "defautPompe": False, "capteurSolOk": True, "bmeOk": True, "npkOk": True, "alerteEngrais": False,
       "alertePlante": False, "seuilStart": 30, "seuilStop": 60}


def test_kit_keys_are_mapped_to_telemetry_v1() -> None:
    mapped = map_kit_payload(KIT)
    assert mapped["soil_moisture_pct"] == 41.5 and mapped["pump_on"] is True
    assert mapped["threshold_start_pct"] == 30 and mapped["threshold_stop_pct"] == 60
    cleaned = clean_metrics(mapped)
    assert cleaned.rejected == ()
    assert cleaned.values["alert_plant"] is False and cleaned.values["n_mgkg"] == 25


def test_out_of_range_values_become_null_and_are_counted() -> None:
    cleaned = clean_metrics({"soil_moisture_pct": 120, "air_temp_c": -40, "pressure_hpa": 500, "n_mgkg": 2000,
                             "p_mgkg": 12.5, "threshold_start_pct": 96, "pump_on": "oui", "unknown": 1,
                             "air_humidity_pct": float("nan")})
    values = cleaned.values
    assert values["soil_moisture_pct"] is None and values["air_temp_c"] is None
    assert values["pressure_hpa"] is None and values["n_mgkg"] is None
    assert values["threshold_start_pct"] is None
    assert len(cleaned.rejected) >= 8


def _batch(client: TestClient, headers: dict, points: list[dict]) -> dict:
    response = client.post("/v1/telemetry/batch", headers=headers, json={"points": points})
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_device_key_ingest_is_idempotent(client: TestClient, world: World, db: Session) -> None:
    key = {"X-Device-Key": world.device_key}
    first = _batch(client, key, [point(soil_moisture_pct=40.0), point(ts=NOW - timedelta(minutes=1))])
    assert first == {"accepted": 2, "duplicates": 0, "rejected_points": 0, "rejected_values": 0}
    second = _batch(client, key, [point(soil_moisture_pct=40.0)])
    assert second["accepted"] == 0 and second["duplicates"] == 1
    assert db.scalar(select(func.count()).select_from(Measurement)) == 2
    device = db.scalars(select(Device).where(Device.serial == SERIAL_A)).one()
    assert device.last_seen_at is not None


def test_raw_kit_payload_and_implausible_timestamp(client: TestClient, world: World) -> None:
    key = {"X-Device-Key": world.device_key}
    kit_point = {**point(), "m": None, "kit": KIT}
    future = point(ts=NOW + timedelta(hours=2))
    result = _batch(client, key, [kit_point, future])
    assert result["accepted"] == 1 and result["rejected_points"] == 1


def test_batch_over_1000_points_is_rejected(client: TestClient, world: World) -> None:
    points = [point(ts=NOW - timedelta(seconds=i + 1)) for i in range(1001)]
    response = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                           json={"points": points})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "BATCH_TOO_LARGE"


def test_wrong_device_key_and_mismatched_serial(client: TestClient, world: World) -> None:
    bad = client.post("/v1/telemetry/batch", headers={"X-Device-Key": "x" * 43}, json={"points": [point()]})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "DEVICE_KEY_INVALID"
    other = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                        json={"points": [point(serial=SERIAL_B)]})
    assert other.status_code == 403 and other.json()["error"]["code"] == "DEVICE_MISMATCH"


def test_relay_ingest_with_user_token(client: TestClient, world: World) -> None:
    assert _batch(client, world.farmer_a, [point()])["accepted"] == 1
    foreign = client.post("/v1/telemetry/batch", headers=world.admin_b, json={"points": [point()]})
    assert foreign.status_code == 404
    anonymous = client.post("/v1/telemetry/batch", json={"points": [point()]})
    assert anonymous.status_code == 401


def test_point_requires_exactly_one_payload(client: TestClient, world: World) -> None:
    both = {**point(), "kit": KIT}
    response = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                           json={"points": [both]})
    assert response.status_code == 422

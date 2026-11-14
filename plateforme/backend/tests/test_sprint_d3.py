"""Tests Sprint D3 : kit_parameters (GET + POST ack) et device_health (GET health + provenance alertes)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from tests.conftest import NOW, World, point


def test_kit_parameters_and_ack(client: TestClient, world: World) -> None:
    """`GET /v1/devices/{id}/parameters` et `POST /v1/devices/{id}/parameters/ack` respectent doc 16 §6.1."""
    cyc = client.post(
        f"/v1/fields/{world.field_id}/crop-cycles",
        headers=world.admin_a,
        json={"crop": "onion", "variety": "Violet de Galmi", "planted_on": "2026-10-01"},
    )
    assert cyc.status_code == 201, cyc.text

    res = client.get(f"/v1/devices/{world.device_id}/parameters", headers=world.farmer_a)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["device_id"] == str(world.device_id)
    assert data["version"] == 1
    assert data["seuils"] == {"start": 30, "stop": 60}
    assert data["npk"] == {"n": 20, "p": 10, "k": 80}
    assert data["etalonnage"] == {"adc_sec": 3200, "adc_eau": 1350}
    assert data["agro"]["culture"] == "onion"
    assert data["agro"]["kc"] is not None
    assert data["applied"] is False
    assert data["provenance"]["seuils"]["model_name"] == "irr_water_balance"
    assert data["provenance"]["npk"]["model_name"] == "fert_reco"
    assert data["provenance"]["etalonnage"]["model_name"] == "sm_calibration"
    assert data["provenance"]["agro"]["model_name"] == "phenology_stage"

    # Acquittement par l'agriculteur
    ack = client.post(
        f"/v1/devices/{world.device_id}/parameters/ack",
        headers=world.farmer_a,
        json={"version": 1, "applied": True},
    )
    assert ack.status_code == 200, ack.text
    assert ack.json()["data"]["applied"] is True

    # Version inconnue -> 404 NOT_FOUND
    missing = client.post(
        f"/v1/devices/{world.device_id}/parameters/ack",
        headers=world.farmer_a,
        json={"version": 99, "applied": True},
    )
    assert missing.status_code == 404

    # Isolation multi-organisation -> 404 NOT_FOUND
    foreign = client.get(f"/v1/devices/{world.device_id}/parameters", headers=world.admin_b)
    assert foreign.status_code == 404


def test_device_health_and_alerts_provenance(client: TestClient, world: World) -> None:
    """`GET /v1/devices/{id}/health` et `GET /v1/alerts` exposent l'état capteurs et la provenance."""
    pts = [
        point(
            ts=NOW - timedelta(minutes=5),
            soil_moisture_pct=25.0,
            air_temp_c=27.0,
            soil_sensor_ok=False,
            bme_ok=True,
            npk_ok=True,
            pump_fault=True,
        )
    ]
    ing = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key}, json={"points": pts})
    assert ing.status_code == 200

    health_res = client.get(f"/v1/devices/{world.device_id}/health", headers=world.farmer_a)
    assert health_res.status_code == 200, health_res.text
    health = health_res.json()["data"]
    assert health["device_id"] == str(world.device_id)
    by_sensor = {s["sensor"]: s for s in health["sensors"]}
    assert set(by_sensor) == {"soil", "bme", "npk", "flow", "pump", "battery"}
    assert by_sensor["soil"]["state"] == "fault"
    assert by_sensor["soil"]["since"] is not None
    assert by_sensor["bme"]["state"] == "ok"
    assert by_sensor["pump"]["state"] == "fault"
    assert health["pump_failure_48h"] is None
    assert health["provenance"]["model_name"] == "anomaly_rules"
    assert health["provenance"]["source"] == "rules"
    assert health["provenance"]["stale"] is False

    # Vérifie que les alertes générées portent elles aussi le bloc provenance (AlertSchema)
    alerts_res = client.get("/v1/alerts", headers=world.farmer_a)
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()["data"]
    assert len(alerts) >= 2
    for alert in alerts:
        assert alert["provenance"]["model_name"] == "anomaly_rules"
        assert alert["provenance"]["source"] == "rules"

    # Acquittement d'alerte conserve la provenance
    ack_res = client.post(f"/v1/alerts/{alerts[0]['id']}/ack", headers=world.farmer_a)
    assert ack_res.status_code == 200
    assert ack_res.json()["data"]["status"] == "acknowledged"
    assert ack_res.json()["data"]["provenance"]["model_name"] == "anomaly_rules"

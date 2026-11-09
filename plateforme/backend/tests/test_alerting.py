"""Alertes : règles pures, anti-rebond, résolution, acquittement, diagnostics et balayage des kits muets."""

from __future__ import annotations

import uuid
from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Alert, Device
from app.jobs.alert_sweep import run_once
from app.services.alerting import DEVICE_SILENT, DRY_SOIL, SOIL_SENSOR_FAILURE, disease_draft, dry_soil_state
from tests.conftest import NOW, SERIAL_A, World, make_settings, point

WINDOW = timedelta(hours=2)


def reading(minutes_ago: int, moisture: float) -> SimpleNamespace:
    return SimpleNamespace(ts=NOW - timedelta(minutes=minutes_ago), soil_moisture_pct=moisture)


def diagnosis(hours_ago: float, label: str = "sick", confidence: float = 0.9, code: str | None = "mildiou") -> Any:
    return SimpleNamespace(captured_at=NOW - timedelta(hours=hours_ago), label=label, confidence=confidence,
                           disease_code=code)


def send(client: TestClient, world: World, minutes_ago: int, **metrics: Any) -> None:
    response = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                           json={"points": [point(ts=NOW - timedelta(minutes=minutes_ago), **metrics)]})
    assert response.status_code == 200, response.text


def alerts(client: TestClient, headers: dict[str, str], **params: str) -> list[dict[str, Any]]:
    response = client.get("/v1/alerts", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def diagnose(client: TestClient, headers: dict[str, str], label: str = "sick", **extra: Any) -> Any:
    body = {"device": SERIAL_A, "label": label, "confidence": 0.92, "model_version": "vision-0.3",
            "disease_code": "mildiou", **extra}
    return client.post("/v1/diagnoses", headers=headers, json=body)


# --- Règles pures ------------------------------------------------------------------------------

@pytest.mark.parametrize(("readings", "expected"), [
    ([], "keep"),
    ([reading(100, 20), reading(50, 20), reading(5, 35)], "resolve"),
    ([reading(100, 20), reading(5, 20)], "keep"),
    ([reading(100, 20), reading(50, 22), reading(5, 21)], "raise"),
    ([reading(60, 20), reading(30, 22), reading(5, 21)], "keep"),
    ([reading(100, 20), reading(50, 31), reading(5, 21)], "keep"),
])
def test_dry_soil_state(readings: list[Any], expected: str) -> None:
    assert dry_soil_state(readings, 30, WINDOW) == expected


def test_disease_draft_requires_consecutive_confident_recent_verdicts() -> None:
    settings = make_settings()
    draft = disease_draft([diagnosis(0), diagnosis(1, code="alternariose"), diagnosis(2)], settings)
    assert draft is not None and draft.severity == "critical"
    assert draft.details == {"disease_codes": ["alternariose", "mildiou"], "count": 3}
    mixed = disease_draft([diagnosis(0), diagnosis(1, "suspect"), diagnosis(2)], settings)
    assert mixed is not None and mixed.severity == "warning"
    assert disease_draft([diagnosis(0), diagnosis(1)], settings) is None
    assert disease_draft([diagnosis(0), diagnosis(1, "healthy"), diagnosis(2)], settings) is None
    assert disease_draft([diagnosis(0), diagnosis(1, confidence=0.5), diagnosis(2)], settings) is None
    assert disease_draft([diagnosis(0), diagnosis(1), diagnosis(49)], settings) is None


# --- Règles déclenchées par l'ingestion --------------------------------------------------------

def test_sensor_failure_is_debounced_acknowledged_then_resolved(client: TestClient, world: World) -> None:
    send(client, world, 20, soil_moisture_pct=40.0, soil_sensor_ok=False)
    send(client, world, 10, soil_moisture_pct=40.0, soil_sensor_ok=False)
    [alert] = alerts(client, world.farmer_a, status="open")
    assert (alert["rule"], alert["severity"], alert["device_id"]) == (SOIL_SENSOR_FAILURE, "critical",
                                                                      world.device_id)
    acked = client.post(f"/v1/alerts/{alert['id']}/ack", headers=world.farmer_a)
    assert acked.status_code == 200 and acked.json()["data"]["status"] == "acknowledged"
    assert client.post(f"/v1/alerts/{alert['id']}/ack", headers=world.admin_b).status_code == 404
    send(client, world, 5, soil_moisture_pct=40.0, soil_sensor_ok=True)
    [resolved] = alerts(client, world.farmer_a, status="resolved")
    assert resolved["id"] == alert["id"] and resolved["resolved_at"] is not None
    assert alerts(client, world.admin_b) == []


def test_persistent_dry_soil_raises_then_resolves(client: TestClient, world: World) -> None:
    thresholds = {"threshold_start_pct": 30, "threshold_stop_pct": 60}
    for minutes_ago, moisture in ((100, 20.0), (50, 22.0), (5, 21.0)):
        send(client, world, minutes_ago, soil_moisture_pct=moisture, **thresholds)
    [alert] = alerts(client, world.farmer_a, status="open")
    assert alert["rule"] == DRY_SOIL and alert["details"]["start_pct"] == 30
    send(client, world, 1, soil_moisture_pct=45.0, **thresholds)
    assert alerts(client, world.farmer_a, status="open") == []


def test_ack_unknown_alert_is_404(client: TestClient, world: World) -> None:
    assert client.post(f"/v1/alerts/{uuid.uuid4()}/ack", headers=world.farmer_a).status_code == 404


# --- Diagnostics -------------------------------------------------------------------------------

def test_three_sick_diagnoses_raise_a_single_alert(client: TestClient, world: World) -> None:
    first, second = diagnose(client, world.agronomist_a), diagnose(client, world.agronomist_a)
    assert first.status_code == second.status_code == 201 and second.json()["data"]["alert"] is None
    third = diagnose(client, world.agronomist_a).json()["data"]
    assert third["alert"] is not None and third["alert"]["severity"] == "critical"
    assert diagnose(client, world.agronomist_a).json()["data"]["alert"] is None
    assert len(alerts(client, world.farmer_a, status="open")) == 1


def test_diagnosis_on_foreign_device_is_404(client: TestClient, world: World) -> None:
    response = diagnose(client, world.admin_b)
    assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"


# --- Tâche périodique --------------------------------------------------------------------------

def test_alert_sweep_flags_silent_devices_once(app: Any, db: Session, settings: Settings, world: World) -> None:
    device = db.scalars(select(Device)).one()
    device.last_seen_at = NOW - timedelta(hours=settings.device_silent_hours + 1)
    db.commit()
    assert run_once(app.state.session_factory, settings, NOW) == 1
    assert run_once(app.state.session_factory, settings, NOW) == 0
    db.expire_all()
    assert [(row.rule, row.status) for row in db.scalars(select(Alert))] == [(DEVICE_SILENT, "open")]


def test_new_telemetry_resolves_silent_alert(app: Any, client: TestClient, db: Session, settings: Settings,
                                             world: World) -> None:
    device = db.scalars(select(Device)).one()
    device.last_seen_at = NOW - timedelta(hours=settings.device_silent_hours + 1)
    db.commit()
    run_once(app.state.session_factory, settings, NOW)
    send(client, world, 1, soil_moisture_pct=40.0)
    db.expire_all()
    assert db.scalars(select(Alert)).one().status == "resolved"

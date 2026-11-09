"""Pont MQTT : logique de traitement sans paho (sujets, charges utiles, acquittements, boîte d'envoi)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Device, DeviceThreshold, Measurement
from app.ingestion.mqtt_bridge import (
    MAX_PAYLOAD_BYTES,
    command_topic,
    handle_message,
    parse_mqtt_url,
    publish_pending_commands,
)
from tests.conftest import NOW, SERIAL_A, SERIAL_B, World, point

TOPIC = f"agri92/v1/devices/{SERIAL_A}"


def handle(db: Session, settings: Settings, suffix: str, payload: Any) -> Any:
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    result = handle_message(f"{TOPIC}/{suffix}", raw, db, settings, NOW)
    db.commit()
    return result


def measurement_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Measurement))


def set_thresholds(client: TestClient, world: World) -> str:
    response = client.put(f"/v1/devices/{world.device_id}/thresholds", headers=world.admin_a,
                          json={"start": 30, "stop": 60})
    assert response.status_code == 200, response.text
    return response.json()["data"]["command_id"]


def test_parse_mqtt_url() -> None:
    plain = parse_mqtt_url("mqtt://broker:1883")
    assert (plain.host, plain.port, plain.tls) == ("broker", 1883, False)
    secure = parse_mqtt_url("mqtts://pont%40agri:mot%2Fpasse@broker.example")
    assert (secure.port, secure.tls, secure.username, secure.password) == (8883, True, "pont@agri", "mot/passe")
    for url in ("http://broker", "mqtt://", "broker:1883"):
        with pytest.raises(ValueError):
            parse_mqtt_url(url)


def test_topic_outside_contract_is_ignored(db: Session, settings: Settings) -> None:
    result = handle_message("agri92/v1/devices/SA92-1/telemetry", b"{}", db, settings, NOW)
    assert (result.kind, result.outcome) == ("unknown", "ignored")


@pytest.mark.parametrize("payload", [b"pas du json", b"[1, 2]", b"\xff\xfe", b"{" + b" " * MAX_PAYLOAD_BYTES + b"}"])
def test_bad_payload_is_rejected(db: Session, settings: Settings, world: World, payload: bytes) -> None:
    assert handle(db, settings, "telemetry", payload).outcome == "rejected"


def test_unknown_device_is_ignored(db: Session, settings: Settings, world: World) -> None:
    result = handle_message(f"agri92/v1/devices/{SERIAL_B}/telemetry", b"{}", db, settings, NOW)
    assert (result.outcome, result.serial) == ("ignored", SERIAL_B)


def test_telemetry_v1_and_raw_firmware_payloads_are_ingested(db: Session, settings: Settings,
                                                             world: World) -> None:
    assert handle(db, settings, "telemetry", point()).outcome == "ingested"
    raw = handle(db, settings, "telemetry", {"soil": 35.5, "temp": 29.1})
    assert raw.outcome == "ingested"
    assert measurement_count(db) == 2


def test_serial_mismatch_between_topic_and_body_is_rejected(db: Session, settings: Settings,
                                                            world: World) -> None:
    result = handle(db, settings, "telemetry", point(serial=SERIAL_B))
    assert result.outcome == "rejected" and measurement_count(db) == 0


def test_ack_applies_only_the_current_command(client: TestClient, db: Session, settings: Settings,
                                              world: World) -> None:
    command_id = set_thresholds(client, world)
    assert handle(db, settings, "commands/ack", {"id": str(uuid.uuid4()), "ok": True}).outcome == "ignored"
    assert handle(db, settings, "commands/ack", {"id": command_id, "ok": "oui"}).outcome == "rejected"
    assert handle(db, settings, "commands/ack", {"id": command_id, "ok": True}).outcome == "applied"
    row = db.scalars(select(DeviceThreshold)).one()
    db.refresh(row)
    assert row.sync_status == "applied" and (row.reported_start_pct, row.reported_stop_pct) == (30, 60)


def test_event_updates_last_seen(db: Session, settings: Settings, world: World) -> None:
    assert handle(db, settings, "events", {"type": "boot"}).outcome == "logged"
    assert handle(db, settings, "events", {"type": ""}).outcome == "rejected"
    device = db.get(Device, uuid.UUID(world.device_id))
    db.refresh(device)
    assert device.last_seen_at is not None


def test_pending_commands_are_published_once(client: TestClient, db: Session, world: World) -> None:
    command_id = set_thresholds(client, world)
    sent: list[tuple[str, dict[str, Any]]] = []

    def publish(topic: str, payload: bytes) -> bool:
        sent.append((topic, json.loads(payload)))
        return True

    assert publish_pending_commands(db, publish, NOW) == 1
    db.commit()
    assert sent == [(command_topic(SERIAL_A), {"cmd": "set_thresholds", "id": command_id, "start": 30, "stop": 60})]
    assert publish_pending_commands(db, publish, NOW) == 0


def test_failed_publish_keeps_command_pending(client: TestClient, db: Session, world: World) -> None:
    set_thresholds(client, world)
    assert publish_pending_commands(db, lambda _topic, _payload: False, NOW) == 0
    assert db.scalars(select(DeviceThreshold)).one().sync_status == "pending"

"""Isolation entre organisations : toute ressource d'une autre organisation répond 404."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Device
from app.services.alerting import AlertDraft, raise_alert
from tests.conftest import NOW, SERIAL_A, World, point


@pytest.fixture
def ids(client: TestClient, db: Session, world: World) -> dict[str, str]:
    """Ressources de l'organisation A : campagne, équipement, cycle, alerte."""
    admin = world.admin_a
    campaign = client.post("/v1/campaigns", headers=admin, json={
        "name": "Hivernage 2026", "season": "rainy", "start_date": "2026-07-01", "end_date": "2026-11-30"})
    equipment = client.post("/v1/equipment", headers=admin, json={
        "farm_id": world.farm_id, "kind": "pump", "label": "Pompe solaire"})
    cycle = client.post(f"/v1/fields/{world.field_id}/crop-cycles", headers=admin, json={
        "crop": "onion", "planted_on": "2026-10-01", "expected_harvest_on": "2027-01-15"})
    assert campaign.status_code == equipment.status_code == cycle.status_code == 201, cycle.text
    device = db.get(Device, uuid.UUID(world.device_id))
    alert = raise_alert(db, device, AlertDraft("dry_soil_persistent", "warning", "Sol sec"), NOW)
    db.commit()
    return {"campaign": campaign.json()["data"]["id"], "equipment": equipment.json()["data"]["id"],
            "cycle": cycle.json()["data"]["id"], "alert": str(alert.id)}


def _requests(world: World, ids: dict[str, str]) -> list[tuple[str, str, dict[str, Any] | None]]:
    field, farm, device = world.field_id, world.farm_id, world.device_id
    return [
        ("GET", f"/v1/farms/{farm}/fields", None),
        ("POST", f"/v1/farms/{farm}/fields", {"name": "Intrus", "area_ha": 0.1}),
        ("GET", f"/v1/farms/{farm}/map", None),
        ("GET", f"/v1/fields/{field}", None),
        ("GET", f"/v1/fields/{field}/recommendations", None),
        ("GET", f"/v1/fields/{field}/weather", None),
        ("GET", f"/v1/fields/{field}/yield-forecast", None),
        ("GET", f"/v1/fields/{field}/crop-cycles", None),
        ("POST", f"/v1/fields/{field}/crop-cycles", {"crop": "onion", "planted_on": "2026-10-01"}),
        ("PATCH", f"/v1/crop-cycles/{ids['cycle']}", {"status": "harvested"}),
        ("GET", f"/v1/devices/{device}", None),
        ("GET", f"/v1/devices/{SERIAL_A}", None),
        ("GET", f"/v1/devices/{device}/thresholds", None),
        ("PUT", f"/v1/devices/{device}/thresholds", {"start": 30, "stop": 60}),
        ("GET", f"/v1/devices/{device}/measurements", None),
        ("POST", "/v1/telemetry/batch", {"points": [point()]}),
        ("POST", f"/v1/alerts/{ids['alert']}/ack", None),
        ("POST", "/v1/diagnoses", {"device": SERIAL_A, "label": "sick", "confidence": 0.9, "model_version": "v1"}),
        ("GET", f"/v1/campaigns/{ids['campaign']}", None),
        ("PATCH", f"/v1/campaigns/{ids['campaign']}", {"status": "active"}),
        ("GET", f"/v1/campaigns/{ids['campaign']}/summary", None),
        ("PATCH", f"/v1/equipment/{ids['equipment']}", {"status": "maintenance"}),
        ("GET", f"/v1/equipment/{ids['equipment']}/maintenance", None),
        ("POST", f"/v1/equipment/{ids['equipment']}/maintenance", {"kind": "corrective"}),
        ("POST", "/v1/equipment", {"farm_id": farm, "kind": "pump", "label": "Intrus"}),
        ("GET", f"/v1/reports/kpis?scope=farm&id={farm}", None),
    ]


def test_every_foreign_resource_answers_404(client: TestClient, world: World, ids: dict[str, str]) -> None:
    failures = []
    for method, url, body in _requests(world, ids):
        response = client.request(method, url, headers=world.admin_b, json=body)
        if response.status_code != 404:
            failures.append((method, url, response.status_code, response.text[:200]))
    assert failures == [], "\n".join(map(str, failures))


def test_foreign_404_matches_unknown_resource(client: TestClient, world: World) -> None:
    foreign = client.get(f"/v1/fields/{world.field_id}", headers=world.admin_b).json()
    unknown = client.get(f"/v1/fields/{uuid.uuid4()}", headers=world.admin_b).json()
    assert foreign["error"]["code"] == unknown["error"]["code"] == "NOT_FOUND"
    assert foreign["error"]["message"] == unknown["error"]["message"]


def test_lists_do_not_leak_other_organization(client: TestClient, world: World, ids: dict[str, str]) -> None:
    for url in ("/v1/farms", "/v1/devices", "/v1/alerts", "/v1/campaigns", "/v1/equipment"):
        body = client.get(url, headers=world.admin_b).json()
        assert body["success"] is True and body["data"] == [], url


def test_owner_can_read_field_detail(client: TestClient, world: World, ids: dict[str, str]) -> None:
    data = client.get(f"/v1/fields/{world.field_id}", headers=world.farmer_a).json()["data"]
    assert data["id"] == world.field_id and data["farm_id"] == world.farm_id
    assert data["centroid"] is not None and data["geometry"]["type"] == "Polygon"
    assert data["active_cycle"]["id"] == ids["cycle"]

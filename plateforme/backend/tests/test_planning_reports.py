"""Campagnes, cycles de culture, équipements, maintenance, indicateurs et export CSV."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.kpis import PUMP_GAP_CAP, device_stats
from app.services.reports import CSV_COLUMNS, report_csv, safe_cell
from tests.conftest import NOW, World, point

KPIS = "/v1/reports/kpis"
EXPORT = "/v1/reports/export.csv"
TODAY = NOW.date()


def error_code(response: Any) -> str:
    return response.json()["error"]["code"]


def create_campaign(client: TestClient, headers: dict[str, str], **overrides: Any) -> Any:
    body = {"name": "Contre-saison 2026", "season": "dry", "start_date": (TODAY - timedelta(days=20)).isoformat(),
            "end_date": (TODAY + timedelta(days=60)).isoformat(), "status": "active", **overrides}
    return client.post("/v1/campaigns", headers=headers, json=body)


def create_cycle(client: TestClient, world: World, **overrides: Any) -> Any:
    body = {"crop": "onion", "planted_on": (TODAY - timedelta(days=10)).isoformat(), **overrides}
    return client.post(f"/v1/fields/{world.field_id}/crop-cycles", headers=world.farmer_a, json=body)


def create_pump(client: TestClient, world: World, **overrides: Any) -> Any:
    body = {"farm_id": world.farm_id, "kind": "pump", "label": "Pompe solaire", "device": world.device_id,
            "flow_m3h": 3.0, **overrides}
    return client.post("/v1/equipment", headers=world.farmer_a, json=body)


def send_pump_cycle(client: TestClient, world: World) -> None:
    """Arrêt, marche, marche, arrêt toutes les 10 min : 1 démarrage, 20 min de pompage."""
    states = (False, True, True, False)
    points = [point(ts=NOW - timedelta(minutes=60 - 10 * index), soil_moisture_pct=30.0, pump_on=state)
              for index, state in enumerate(states)]
    response = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                           json={"points": points})
    assert response.status_code == 200, response.text


# --- Fonctions pures ---------------------------------------------------------------------------

def test_safe_cell_neutralises_formulas() -> None:
    for value in ("=HYPERLINK(\"http://x\")", "+1", "-2", "@SUM(A1)", "\tx", "\rx"):
        assert safe_cell(value) == "'" + value
    assert (safe_cell("oignon"), safe_cell(None), safe_cell(3.5)) == ("oignon", "", 3.5)


def test_report_csv_has_bom_header_and_long_format() -> None:
    report = {"scope": "farm", "scope_id": "f1", "from": "a", "to": "b",
              "kpis": {"devices": 2, "alerts_by_rule": {"dry_soil": 3, "=evil": 1}, "water_m3": None}}
    raw = report_csv(report)
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    assert tuple(rows[0]) == CSV_COLUMNS
    assert rows[1:] == [["farm", "f1", "a", "b", "devices", "", "2"],
                        ["farm", "f1", "a", "b", "alerts_by_rule", "'=evil", "1"],
                        ["farm", "f1", "a", "b", "alerts_by_rule", "dry_soil", "3"],
                        ["farm", "f1", "a", "b", "water_m3", "", ""]]


def test_device_stats_caps_gaps_and_counts_starts() -> None:
    start = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)
    rows = [(start, False), (start + timedelta(minutes=10), True), (start + timedelta(minutes=20), True),
            (start + timedelta(minutes=140), False), (start + timedelta(minutes=150), True)]
    stats = device_stats(rows)
    capped_minutes = 10 + PUMP_GAP_CAP.total_seconds() / 60
    assert (stats.points, stats.irrigation_events, stats.active_hours) == (5, 2, 2)
    assert stats.pump_hours == pytest.approx(capped_minutes / 60)


def test_device_stats_without_rows_is_zero() -> None:
    stats = device_stats([])
    assert (stats.points, stats.irrigation_events, stats.pump_hours, stats.active_hours) == (0, 0, 0.0, 0)


# --- Indicateurs et export ---------------------------------------------------------------------

def test_kpis_follow_telemetry_and_pump_flow(client: TestClient, world: World) -> None:
    assert create_pump(client, world).status_code == 201
    send_pump_cycle(client, world)
    response = client.get(KPIS, headers=world.farmer_a, params={"scope": "farm", "id": world.farm_id})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert (data["scope"], data["scope_id"]) == ("farm", world.farm_id)
    indicators = data["kpis"]
    assert (indicators["devices"], indicators["fields"], indicators["measurements"]) == (1, 1, 4)
    assert indicators["irrigation_events"] == 1 and indicators["devices_without_flow"] == 0
    assert indicators["pump_hours"] == pytest.approx(0.33)
    assert indicators["water_m3"] == pytest.approx(1.0, abs=0.02)


@pytest.mark.parametrize(("params", "code"), [
    ({"from": "2025-01-01T00:00:00Z", "to": "2026-03-01T00:00:00Z"}, "RANGE_TOO_LARGE"),
    ({"from": "2026-03-01T00:00:00Z", "to": "2026-03-01T00:00:00Z"}, "INVALID_RANGE"),
    ({"scope": "planete"}, "INVALID_SCOPE"),
    ({"scope": "farm"}, "SCOPE_ID_REQUIRED"),
])
def test_kpis_reject_bad_parameters(client: TestClient, world: World, params: dict[str, str], code: str) -> None:
    response = client.get(KPIS, headers=world.admin_a, params=params)
    assert response.status_code == 400 and error_code(response) == code


def test_kpis_default_period_is_last_30_days(client: TestClient, world: World) -> None:
    data = client.get(KPIS, headers=world.admin_a).json()["data"]
    assert data["scope"] == "org" and data["to"] == NOW.isoformat()
    assert data["from"] == (NOW - timedelta(days=30)).isoformat()


def test_export_csv_is_attachment_with_bom(client: TestClient, world: World) -> None:
    response = client.get(EXPORT, headers=world.admin_a, params={"scope": "farm", "id": world.farm_id})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == f'attachment; filename="kpis-farm-{NOW:%Y%m%d}.csv"'
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.content.decode("utf-8-sig").splitlines()[0] == ",".join(CSV_COLUMNS)


# --- Campagnes et cycles -----------------------------------------------------------------------

def test_campaign_lifecycle_and_summary(client: TestClient, world: World) -> None:
    created = create_campaign(client, world.admin_a)
    assert created.status_code == 201, created.text
    campaign = created.json()["data"]
    assert campaign["organization_id"] == str(world.org_a)
    cycle = create_cycle(client, world, campaign_id=campaign["id"])
    assert cycle.status_code == 201, cycle.text
    patched = client.patch(f"/v1/campaigns/{campaign['id']}", headers=world.admin_a, json={"name": "Saison sèche"})
    assert patched.status_code == 200 and patched.json()["data"]["name"] == "Saison sèche"
    listed = client.get("/v1/campaigns", headers=world.farmer_a, params={"status": "active"}).json()
    assert [item["id"] for item in listed["data"]] == [campaign["id"]] and listed["meta"]["total"] == 1
    summary = client.get(f"/v1/campaigns/{campaign['id']}/summary", headers=world.farmer_a).json()["data"]
    assert summary["fields"] == 1 and summary["crops"] == {"onion": 1}
    assert summary["alerts_total"] == 0 and summary["campaign"]["name"] == "Saison sèche"


def test_campaign_rules(client: TestClient, world: World) -> None:
    assert create_campaign(client, world.farmer_a).status_code == 403
    reversed_dates = create_campaign(client, world.admin_a, start_date="2026-06-01", end_date="2026-05-01")
    assert reversed_dates.status_code == 400 and error_code(reversed_dates) == "INVALID_DATES"
    assert create_campaign(client, world.admin_a, season="hiver").status_code == 422


def test_crop_cycle_create_list_and_harvest(client: TestClient, world: World) -> None:
    cycle = create_cycle(client, world).json()["data"]
    listed = client.get(f"/v1/fields/{world.field_id}/crop-cycles", headers=world.agronomist_a)
    assert [item["id"] for item in listed.json()["data"]] == [cycle["id"]]
    url = f"/v1/crop-cycles/{cycle['id']}"
    missing = client.patch(url, headers=world.farmer_a, json={"status": "harvested"})
    assert missing.status_code == 400 and error_code(missing) == "HARVEST_DATE_REQUIRED"
    early = client.patch(url, headers=world.farmer_a,
                         json={"status": "harvested", "harvested_on": (TODAY - timedelta(days=30)).isoformat()})
    assert early.status_code == 400 and error_code(early) == "INVALID_DATES"
    done = client.patch(url, headers=world.farmer_a,
                        json={"status": "harvested", "harvested_on": TODAY.isoformat(), "yield_kg": 1200})
    assert done.status_code == 200, done.text
    assert done.json()["data"]["status"] == "harvested"


def test_crop_code_must_match_pattern(client: TestClient, world: World) -> None:
    assert create_cycle(client, world, crop="Oignon!").status_code == 422


# --- Équipements et maintenance ----------------------------------------------------------------

def test_equipment_and_maintenance(client: TestClient, world: World) -> None:
    created = create_pump(client, world)
    assert created.status_code == 201, created.text
    item = created.json()["data"]
    assert item["device_id"] == world.device_id and item["flow_m3h"] == 3.0
    patched = client.patch(f"/v1/equipment/{item['id']}", headers=world.farmer_a, json={"status": "maintenance"})
    assert patched.status_code == 200 and patched.json()["data"]["status"] == "maintenance"
    url = f"/v1/equipment/{item['id']}/maintenance"
    event = client.post(url, headers=world.agronomist_a, json={"kind": "inspection", "notes": "Joint usé"})
    assert event.status_code == 201, event.text
    future = client.post(url, headers=world.farmer_a,
                         json={"kind": "corrective", "ts": (NOW + timedelta(days=1)).isoformat()})
    assert future.status_code == 400 and error_code(future) == "INVALID_DATES"
    history = client.get(url, headers=world.farmer_a).json()["data"]
    assert [entry["notes"] for entry in history] == ["Joint usé"]
    listed = client.get("/v1/equipment", headers=world.farmer_a, params={"kind": "pump"}).json()["data"]
    assert [entry["id"] for entry in listed] == [item["id"]]


def test_equipment_rules(client: TestClient, world: World) -> None:
    assert create_pump(client, world, flow_m3h=0).status_code == 422
    unknown = create_pump(client, world, device="SA92-999999")
    assert unknown.status_code == 404 and error_code(unknown) == "NOT_FOUND"
    other_farm = client.post("/v1/farms", headers=world.admin_a, json={
        "name": "Ferme de Notto", "region": "Thiès", "commune": "Notto", "latitude": 14.97, "longitude": -17.0,
        "area_ha": 1.0}).json()["data"]
    elsewhere = create_pump(client, world, farm_id=other_farm["id"])
    assert elsewhere.status_code == 400 and error_code(elsewhere) == "DEVICE_NOT_ON_FARM"

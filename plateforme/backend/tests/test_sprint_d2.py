"""Tests Sprint D2 : mapping d'identifiants hybride, weather, recommendations + feedback et provenance."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.core.config import load_settings
from app.seed import DEMO_IDS, seed
from tests.conftest import NOW, World, point


def test_demo_seed_uses_canonical_uuids_and_resolves_slugs(client: TestClient, app: Any) -> None:
    """`app.seed` crée des UUID v4 déterministes et `parse_uuid` accepte les slugs démo en mode hybride."""
    settings = load_settings({"APP_ENV": "test", "JWT_SECRET": "s" * 48, "DEVICE_KEY_PEPPER": "p" * 48})
    with app.state.session_factory() as session:
        created = seed(session, settings)
        assert created is not None
        session.commit()

    login = client.post(
        "/v1/auth/token",
        json={"username": created.admin_login, "password": created.admin_password},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    # Accès par UUID canonique ET par slug démo (`fld-mboro-1`)
    by_uuid = client.get(f"/v1/fields/{DEMO_IDS['fld-mboro-1']}", headers=headers)
    by_slug = client.get("/v1/fields/fld-mboro-1", headers=headers)
    assert by_uuid.status_code == 200 and by_slug.status_code == 200
    assert by_uuid.json()["data"]["id"] == str(DEMO_IDS["fld-mboro-1"])
    assert by_slug.json()["data"]["id"] == str(DEMO_IDS["fld-mboro-1"])

    # Un slug inconnu reste un vrai 404 NOT_FOUND (pas de repli silencieux)
    unknown = client.get("/v1/fields/fld-inexistant", headers=headers)
    assert unknown.status_code == 404 and unknown.json()["error"]["code"] == "NOT_FOUND"


def test_weather_and_recommendations_contracts_and_provenance(client: TestClient, app: Any, world: World) -> None:
    """`weather` et `recommendations` renvoient une provenance doc 16 §9.2 complète et gèrent le repli météo."""
    pts = [
        point(
            ts=NOW - timedelta(hours=hour),
            soil_moisture_pct=22.0,
            air_temp_c=23.0 + hour,
            n_mgkg=15,
            p_mgkg=18,
            k_mgkg=160,
            threshold_start_pct=30,
            threshold_stop_pct=60,
        )
        for hour in range(1, 7)
    ]
    ingested = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key}, json={"points": pts})
    assert ingested.status_code == 200

    # 1. Weather nominal puis cache
    wx_res = client.get(f"/v1/fields/{world.field_id}/weather", headers=world.farmer_a, params={"days": 3})
    assert wx_res.status_code == 200, wx_res.text
    wx = wx_res.json()["data"]
    assert wx["field_id"] == str(world.field_id)
    assert wx["source"] == "provider"
    assert wx["provenance"]["source"] == "rules"
    assert wx["provenance"]["fallback_step"] == 2
    assert len(wx["days"]) == 3
    assert wx["days"][0]["et0_hargreaves_mm"] is not None

    # 2. Recommendations : utilise l'ET0 météo de repli si < 6 points kit sur 24h
    rec_res = client.get(f"/v1/fields/{world.field_id}/recommendations", headers=world.farmer_a)
    assert rec_res.status_code == 200, rec_res.text
    recs = rec_res.json()["data"]
    assert len(recs) == 2
    irr, fert = recs[0], recs[1]
    assert irr["kind"] == "irrigation"
    assert irr["payload"]["et0_mm"] is not None
    assert irr["payload"]["et0_method"] == "hargreaves"
    assert irr["provenance"]["model_name"] == "irrigation_fao56"
    assert irr["provenance"]["source"] == "rules"
    assert irr["provenance"]["fallback_step"] == 2
    assert fert["kind"] == "fertilization"
    assert fert["provenance"]["model_name"] == "fertility_rules"
    assert fert["provenance"]["source"] == "rules"

    # 3. Feedback sur recommandation + isolation multi-organisation (404)
    fb = client.post(
        f"/v1/recommendations/{irr['id']}/feedback",
        headers=world.farmer_a,
        json={"feedback": "followed"},
    )
    assert fb.status_code == 200
    assert fb.json()["data"]["id"] == irr["id"]
    assert fb.json()["data"]["provenance"]["model_name"] == "irrigation_fao56"

    cross_org = client.get(f"/v1/fields/{world.field_id}/weather", headers=world.admin_b)
    assert cross_org.status_code == 404

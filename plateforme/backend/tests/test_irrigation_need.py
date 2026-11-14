"""Sprint D1 : pluie annoncée dans les recommandations (E2) et route GET /v1/fields/{id}/irrigation-need."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_now
from app.core.errors import AppError
from app.services.agronomy import M3_PER_MM_HA, RAIN_SKIP_MM
from app.services.weather import weather_unavailable
from tests.conftest import NOW, World, point
from tests.test_planning_reports import create_cycle
from tests.test_sprint_d0 import assert_provenance

NEED_KEYS = {"field_id", "window_hours", "need_mm", "volume_m3", "defer", "defer_reason", "rain_expected_mm",
             "provenance"}
FIELD_AREA_HA = 0.5  # parcelle du `world`


class DatedWeather:
    """Fournisseur déterministe dont le premier jour est aujourd'hui (l'horloge des tests est `NOW`)."""

    name = "dated"

    def __init__(self, rain_mm: float | None = 0.0, et0_mm: float | None = 5.5) -> None:
        self.rain_mm, self.et0_mm, self.fail, self.calls = rain_mm, et0_mm, False, 0

    def daily_forecast(self, latitude: float, longitude: float, days: int) -> list[dict[str, Any]]:
        self.calls += 1
        if self.fail:
            raise weather_unavailable()
        return [{"date": (NOW.date() + timedelta(days=i)).isoformat(), "t_max_c": 34.0, "t_min_c": 21.0,
                 "precipitation_mm": self.rain_mm if i == 0 else 0.0, "et0_mm": self.et0_mm} for i in range(days)]


def use_weather(app: Any, **kwargs: Any) -> DatedWeather:
    provider = DatedWeather(**kwargs)
    app.state.weather_provider = provider
    return provider


def need(client: TestClient, world: World, headers: dict[str, str] | None = None) -> Any:
    chosen = world.farmer_a if headers is None else headers
    return client.get(f"/v1/fields/{world.field_id}/irrigation-need", headers=chosen)


def kc_of(client: TestClient, world: World) -> float:
    irrigation = client.get(f"/v1/fields/{world.field_id}/recommendations", headers=world.farmer_a).json()["data"][0]
    return float(irrigation["payload"]["crop_state"]["kc"])


# --- Route : forme et besoin -------------------------------------------------------------------

def test_need_has_exactly_the_contract_shape(client: TestClient, app: Any, world: World) -> None:
    use_weather(app)
    assert create_cycle(client, world).status_code == 201
    body = need(client, world).json()
    assert body["success"] is True
    data = body["data"]
    assert set(data) == NEED_KEYS
    assert data["field_id"] == world.field_id and data["window_hours"] == 24
    assert isinstance(data["defer"], bool)
    assert_provenance(data["provenance"])
    assert (data["provenance"]["source"], data["provenance"]["fallback_step"]) == ("rules", 2)
    assert data["provenance"]["model_name"] == "irrigation_fao56" and data["provenance"]["stale"] is False


def test_need_is_etc_minus_rain_with_net_volume(client: TestClient, app: Any, world: World) -> None:
    use_weather(app, rain_mm=1.0, et0_mm=5.5)
    assert create_cycle(client, world).status_code == 201
    kc = kc_of(client, world)
    data = need(client, world).json()["data"]
    expected = round(max(0.0, kc * 5.5 - 1.0), 2)
    assert data["need_mm"] == pytest.approx(expected, abs=0.01) and data["need_mm"] > 0
    assert data["volume_m3"] == pytest.approx(round(data["need_mm"] * FIELD_AREA_HA * M3_PER_MM_HA, 1), abs=0.1)
    assert data["rain_expected_mm"] == 1.0 and data["defer"] is False and data["defer_reason"] is None


def test_significant_rain_defers_irrigation_but_keeps_the_need(client: TestClient, app: Any, world: World) -> None:
    use_weather(app, rain_mm=RAIN_SKIP_MM + 0.5, et0_mm=30.0)  # ETc > pluie : il reste un besoin
    assert create_cycle(client, world).status_code == 201
    data = need(client, world).json()["data"]
    assert data["need_mm"] > 0 and data["defer"] is True
    assert "Pluie annoncée" in data["defer_reason"] and data["rain_expected_mm"] == RAIN_SKIP_MM + 0.5


def test_rain_covering_the_need_gives_zero_and_no_deferral(client: TestClient, app: Any, world: World) -> None:
    use_weather(app, rain_mm=40.0, et0_mm=5.5)
    assert create_cycle(client, world).status_code == 201
    data = need(client, world).json()["data"]
    assert data["need_mm"] == 0 and data["volume_m3"] == 0 and data["defer"] is False


# --- Route : données manquantes ----------------------------------------------------------------

def test_without_crop_cycle_the_need_is_not_computable(client: TestClient, app: Any, world: World) -> None:
    use_weather(app)
    data = need(client, world).json()["data"]
    assert (data["need_mm"], data["volume_m3"], data["defer"]) == (0, None, False)
    assert "cycle cultural" in data["defer_reason"]
    assert_provenance(data["provenance"])


def test_weather_down_falls_back_to_kit_et0_without_rain(client: TestClient, app: Any, world: World) -> None:
    provider = use_weather(app)
    provider.fail = True
    assert create_cycle(client, world).status_code == 201
    points = [point(ts=NOW - timedelta(hours=h), soil_moisture_pct=30.0, air_temp_c=20.0 + h) for h in range(1, 9)]
    sent = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key}, json={"points": points})
    assert sent.status_code == 200, sent.text
    response = need(client, world)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["rain_expected_mm"] is None and data["defer"] is False and data["need_mm"] > 0
    assert data["provenance"]["data_as_of"] is not None  # dernier relevé du kit


def test_weather_down_and_no_kit_is_not_computable_not_an_error(client: TestClient, app: Any, world: World) -> None:
    use_weather(app).fail = True
    assert create_cycle(client, world).status_code == 201
    response = need(client, world)
    assert response.status_code == 200
    assert response.json()["data"]["defer_reason"].startswith("Besoin non calculable")


def test_stale_cache_is_flagged_in_provenance(client: TestClient, app: Any, world: World) -> None:
    provider = use_weather(app)
    assert create_cycle(client, world).status_code == 201
    assert need(client, world).status_code == 200
    provider.fail = True
    app.dependency_overrides[get_now] = lambda: NOW + timedelta(hours=3)  # cache expiré, fournisseur en panne
    data = need(client, world).json()["data"]
    assert data["provenance"]["stale"] is True and data["provenance"]["data_as_of"] is not None


# --- Route : accès -----------------------------------------------------------------------------

def test_need_is_scoped_to_the_organization(client: TestClient, app: Any, world: World) -> None:
    use_weather(app)
    assert need(client, world, world.admin_b).status_code == 404
    assert need(client, world, {}).status_code == 401
    unknown = client.get("/v1/fields/00000000-0000-0000-0000-000000000000/irrigation-need", headers=world.farmer_a)
    assert unknown.status_code == 404


def test_weather_other_error_is_not_swallowed(client: TestClient, app: Any, world: World) -> None:
    class Broken(DatedWeather):
        def daily_forecast(self, latitude: float, longitude: float, days: int) -> list[dict[str, Any]]:
            raise AppError("BOOM", "panne inattendue", 500)

    app.state.weather_provider = Broken()
    assert create_cycle(client, world).status_code == 201
    assert need(client, world).status_code == 500


# --- E2 : pluie annoncée dans les recommandations ----------------------------------------------

def test_recommendation_holds_back_irrigation_when_rain_is_announced(client: TestClient, app: Any,
                                                                     world: World) -> None:
    use_weather(app, rain_mm=12.0, et0_mm=5.5)
    assert create_cycle(client, world).status_code == 201
    client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                json={"points": [point(ts=NOW - timedelta(hours=1), soil_moisture_pct=20.0)]})
    irrigation = client.get(f"/v1/fields/{world.field_id}/recommendations",
                            headers=world.farmer_a).json()["data"][0]
    assert irrigation["payload"]["rain_expected_mm"] == 12.0
    assert irrigation["payload"]["advice"]["action"] == "surveiller"
    assert "12 mm" in irrigation["payload"]["advice"]["reason"]


def test_recommendation_ignores_rain_when_weather_is_down(client: TestClient, app: Any, world: World) -> None:
    use_weather(app).fail = True
    assert create_cycle(client, world).status_code == 201
    client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                json={"points": [point(ts=NOW - timedelta(hours=1), soil_moisture_pct=20.0)]})
    response = client.get(f"/v1/fields/{world.field_id}/recommendations", headers=world.farmer_a)
    assert response.status_code == 200
    irrigation = response.json()["data"][0]
    assert irrigation["payload"]["rain_expected_mm"] is None and irrigation["payload"]["advice"]["action"] == "irriguer"

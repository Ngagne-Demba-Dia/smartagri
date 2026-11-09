"""Agronomie (FAO-56, seuils, irrigation, fertilité), recommandations et météo avec cache."""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_now
from app.core.errors import AppError
from app.services import agronomy
from app.services.agronomy import IrrigationInput, recommend_irrigation
from app.services.weather import OpenMeteoProvider, parse_open_meteo
from tests.conftest import NOW, World, point

OPEN_METEO = {"daily": {"time": ["2026-10-27", "2026-10-28"], "temperature_2m_max": [35.1, 34.0],
                        "temperature_2m_min": [22.0, None], "precipitation_sum": [0, 1.2],
                        "et0_fao_evapotranspiration": [5.9, 5.4]}}


def irrigation(moisture: float | None, **extra: Any) -> IrrigationInput:
    return IrrigationInput(soil_moisture_pct=moisture, soil_sensor_ok=extra.pop("ok", True), threshold_start_pct=30,
                           threshold_stop_pct=60, **extra)


# --- Seuils du firmware ------------------------------------------------------------------------

@pytest.mark.parametrize(("start", "stop"), [(30, 60), ("30", " 35 "), (0, 5), (95, 100)])
def test_valid_thresholds(start: Any, stop: Any) -> None:
    assert agronomy.validate_thresholds(start, stop) == (int(start), int(str(stop).strip()))


@pytest.mark.parametrize(("start", "stop"), [(30, 34), (-1, 50), (50, 101), (True, 60), (30.5, 60), ("3e1", 60)])
def test_invalid_thresholds(start: Any, stop: Any) -> None:
    with pytest.raises(agronomy.ThresholdError):
        agronomy.validate_thresholds(start, stop)


# --- FAO-56 ------------------------------------------------------------------------------------

def test_extraterrestrial_radiation_matches_fao56_example_8() -> None:
    """FAO-56 exemple 8 : 20° S, 3 septembre (jour 246) → Ra = 32,2 MJ m-2 j-1."""
    assert agronomy.extraterrestrial_radiation(-20.0, 246) == pytest.approx(32.2, abs=0.1)
    with pytest.raises(ValueError):
        agronomy.extraterrestrial_radiation(91.0, 10)


def test_hargreaves_et0() -> None:
    expected = 0.0023 * (25.0 + 17.8) * math.sqrt(14.0) * 0.408 * 32.2
    assert agronomy.hargreaves_et0(32.0, 18.0, 32.2) == pytest.approx(expected)
    assert expected == pytest.approx(4.84, abs=0.01)
    with pytest.raises(ValueError):
        agronomy.hargreaves_et0(18.0, 32.0, 32.2)


def test_kc_curve_and_growth_stage_for_onion() -> None:
    onion = agronomy.crop_profile("onion")
    assert onion.season_days == 150
    assert agronomy.kc_for_day(onion, 0) == 0.70
    assert agronomy.kc_for_day(onion, 15 + 12.5) == pytest.approx((0.70 + 1.05) / 2)
    assert agronomy.kc_for_day(onion, 60) == 1.05 and agronomy.kc_for_day(onion, 400) == 0.75
    stages = [agronomy.growth_stage(onion, day) for day in (0, 15, 40, 110, 150)]
    assert stages == ["initial", "developpement", "mi_saison", "arriere_saison", "apres_recolte"]
    with pytest.raises(ValueError):
        agronomy.crop_profile("baobab")


# --- Irrigation et fertilité -------------------------------------------------------------------

def test_irrigation_advice_actions() -> None:
    assert recommend_irrigation(irrigation(None)).action == "verifier_capteur"
    assert recommend_irrigation(irrigation(20.0, ok=False)).action == "verifier_capteur"
    dry = recommend_irrigation(irrigation(20.0, et0_mm=6.0, kc=1.0, irrigation_type="drip", area_ha=0.5))
    assert (dry.action, dry.etc_mm, dry.net_mm) == ("irriguer", 6.0, 6.0)
    assert dry.gross_mm == pytest.approx(6.67) and dry.volume_m3 == pytest.approx(33.4)
    assert recommend_irrigation(irrigation(20.0, rain_forecast_mm=8.0)).action == "surveiller"
    assert recommend_irrigation(irrigation(35.0)).action == "surveiller"
    assert recommend_irrigation(irrigation(50.0)).action == "ne_pas_irriguer"


def test_fertility_classes_never_give_a_dose() -> None:
    levels = [status.level for status in agronomy.fertility_status(10, 15, 200)]
    assert levels == ["bas", "moyen", "eleve"]
    assert agronomy.fertility_status(None, None, None)[0].level is None
    assert "Aucune dose" in agronomy.FERTILITY_CAVEAT


# --- Recommandations via l'API -----------------------------------------------------------------

def test_field_recommendations_are_reused_and_accept_feedback(client: TestClient, world: World) -> None:
    points = [point(ts=NOW - timedelta(hours=hour), soil_moisture_pct=20.0, air_temp_c=20.0 + hour,
                    n_mgkg=10, p_mgkg=15, k_mgkg=200, threshold_start_pct=30, threshold_stop_pct=60)
              for hour in range(1, 8)]
    sent = client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key}, json={"points": points})
    assert sent.status_code == 200, sent.text
    url = f"/v1/fields/{world.field_id}/recommendations"
    first = client.get(url, headers=world.farmer_a).json()["data"]
    irrigation_row, fertilization_row = first
    assert (irrigation_row["kind"], fertilization_row["kind"]) == ("irrigation", "fertilization")
    payload = irrigation_row["payload"]
    assert payload["advice"]["action"] == "irriguer" and payload["thresholds"]["source"] == "kit"
    assert payload["et0_method"] == "hargreaves" and payload["et0_mm"] > 0
    assert [item["level"] for item in fertilization_row["payload"]["nutrients"]] == ["bas", "moyen", "eleve"]
    again = client.get(url, headers=world.farmer_a).json()["data"]
    assert [row["id"] for row in again] == [row["id"] for row in first]
    feedback = client.post(f"/v1/recommendations/{irrigation_row['id']}/feedback", headers=world.farmer_a,
                           json={"feedback": "followed"})
    assert feedback.status_code == 200, feedback.text
    foreign = client.post(f"/v1/recommendations/{irrigation_row['id']}/feedback", headers=world.admin_b,
                          json={"feedback": "ignored"})
    assert foreign.status_code == 404


# --- Météo -------------------------------------------------------------------------------------

def test_weather_uses_cache_then_stale_cache(client: TestClient, app: Any, world: World) -> None:
    provider = app.state.weather_provider
    url = f"/v1/fields/{world.field_id}/weather"
    first = client.get(url, headers=world.farmer_a, params={"days": 3}).json()["data"]
    assert first["source"] == "provider" and len(first["days"]) == 3 and provider.calls == 1
    assert first["days"][0]["et0_hargreaves_mm"] is not None
    assert client.get(url, headers=world.farmer_a, params={"days": 3}).json()["data"]["source"] == "cache"
    assert provider.calls == 1
    provider.fail = True
    app.dependency_overrides[get_now] = lambda: NOW + timedelta(days=1)  # le cache expire : horloge avancée
    assert client.get(url, headers=world.farmer_a, params={"days": 3}).json()["data"]["source"] == "stale_cache"
    missing = client.get(url, headers=world.farmer_a, params={"days": 5})
    assert missing.status_code == 503 and missing.json()["error"]["code"] == "WEATHER_UNAVAILABLE"
    invalid = client.get(url, headers=world.farmer_a, params={"days": 30})
    assert invalid.status_code == 400 and invalid.json()["error"]["code"] == "INVALID_DAYS"


def test_open_meteo_provider_with_mock_transport() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=OPEN_METEO)

    provider = OpenMeteoProvider("https://meteo.test/v1/forecast", client=httpx.Client(
        transport=httpx.MockTransport(handler)))
    rows = provider.daily_forecast(14.69, -17.44, 2)
    assert rows[0] == {"date": "2026-10-27", "t_max_c": 35.1, "t_min_c": 22.0, "precipitation_mm": 0.0,
                       "et0_mm": 5.9}
    assert rows[1]["t_min_c"] is None
    params = seen[0].url.params
    assert (params["forecast_days"], params["timezone"]) == ("2", "Africa/Dakar")


@pytest.mark.parametrize("payload", [{}, {"daily": {"time": ["d"], "temperature_2m_max": []}},
                                     {"daily": {**OPEN_METEO["daily"], "precipitation_sum": ["x", 1]}}])
def test_open_meteo_rejects_inconsistent_payload(payload: dict[str, Any]) -> None:
    with pytest.raises(AppError) as caught:
        parse_open_meteo(payload)
    assert caught.value.code == "WEATHER_UNAVAILABLE"


def test_open_meteo_http_error_is_503() -> None:
    provider = OpenMeteoProvider("https://meteo.test/v1/forecast", client=httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(500))))
    with pytest.raises(AppError) as caught:
        provider.daily_forecast(14.69, -17.44, 2)
    assert caught.value.status == 503

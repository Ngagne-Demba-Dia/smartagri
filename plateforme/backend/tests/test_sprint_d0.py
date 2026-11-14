"""Sprint D0 : bug E1 (crop), bloc de provenance (doc 16 § 9.2), chaîne de repli, mode hybride par service."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import ConfigError, load_settings
from app.core.errors import AppError
from app.core.service_modes import MOCK, REAL, SERVICES, ServiceModeError, load_service_modes, parse_overrides
from app.db.models import ModelRegistry, Recommendation
from app.services import yield_forecast
from app.services.inference.base import InferenceError
from app.services.inference.fallback import predict_with_fallback
from app.services.provenance import confidence, provenance, rules_provenance
from app.services.recommendations import recommendation_view
from tests.conftest import NOW, World, point
from tests.test_assistant import ask, install, response, text
from tests.test_planning_reports import create_cycle

PROVENANCE_KEYS = {"model_name", "model_version", "source", "fallback_step", "computed_at", "data_as_of",
                   "stale", "confidence"}


def assert_provenance(block: dict[str, Any]) -> None:
    assert set(block) == PROVENANCE_KEYS
    assert block["source"] in {"agriml", "octopus", "rules"} and 0 <= block["fallback_step"] <= 2
    assert set(block["confidence"]) == {"kind", "value", "p10", "p90", "calibrated"}
    datetime.fromisoformat(block["computed_at"])  # ISO 8601 avec fuseau


# --- E1 : `crop` est une chaîne ----------------------------------------------------------------

def test_recommendation_crop_is_a_string_and_detail_is_kept(client: TestClient, world: World) -> None:
    assert create_cycle(client, world).status_code == 201
    client.post("/v1/telemetry/batch", headers={"X-Device-Key": world.device_key},
                json={"points": [point(ts=NOW - timedelta(hours=1), soil_moisture_pct=20.0)]})
    irrigation, fertilization = client.get(f"/v1/fields/{world.field_id}/recommendations",
                                           headers=world.farmer_a).json()["data"]
    assert irrigation["payload"]["crop"] == "onion"
    assert irrigation["payload"]["crop_state"]["crop_name"]
    assert_provenance(irrigation["provenance"])
    assert_provenance(fertilization["provenance"])


def test_recommendation_without_cycle_has_null_crop(client: TestClient, world: World) -> None:
    irrigation = client.get(f"/v1/fields/{world.field_id}/recommendations", headers=world.farmer_a).json()["data"][0]
    assert irrigation["payload"]["crop"] is None and irrigation["payload"]["crop_state"] is None


def test_legacy_row_with_crop_object_is_normalized_without_mutation() -> None:
    legacy = {"crop": "onion", "crop_name": "Oignon", "day": 10}
    row = Recommendation(kind="irrigation", engine_version="regles-fao56-v1", created_at=NOW,
                         payload={"crop": legacy, "measured_at": NOW.isoformat()})
    view = recommendation_view(row)
    assert view["payload"]["crop"] == "onion" and view["payload"]["crop_state"]["day"] == 10
    assert isinstance(row.payload["crop"], dict)  # la ligne stockée n'est pas modifiée
    assert view["provenance"]["data_as_of"] == NOW.isoformat()


# --- Provenance --------------------------------------------------------------------------------

def test_rules_provenance_shape() -> None:
    block = rules_provenance("irrigation_fao56", "regles-fao56-v1", NOW)
    assert_provenance(block)
    assert (block["source"], block["fallback_step"], block["stale"], block["data_as_of"]) == ("rules", 2, False, None)
    assert block["confidence"] == {"kind": "none", "value": None, "p10": None, "p90": None, "calibrated": False}


@pytest.mark.parametrize("kwargs", [
    {"source": "llm"}, {"fallback_step": 3}, {"fallback_step": -1}, {"model_name": ""},
])
def test_provenance_rejects_invalid_blocks(kwargs: dict[str, Any]) -> None:
    base = {"model_name": "m", "model_version": "1", "source": "agriml", "computed_at": NOW}
    with pytest.raises(ValueError):
        provenance(**{**base, **kwargs})


@pytest.mark.parametrize("kwargs", [
    {"kind": "none", "value": 0.5}, {"kind": "interval", "p10": 5.0, "p90": 1.0}, {"kind": "interval"},
    {"kind": "probability", "value": 1.5}, {"kind": "bogus"},
])
def test_confidence_rejects_invalid_blocks(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        confidence(**kwargs)


def test_weather_carries_provenance(client: TestClient, world: World) -> None:
    url = f"/v1/fields/{world.field_id}/weather"
    fresh = client.get(url, headers=world.farmer_a, params={"days": 3}).json()["data"]
    assert_provenance(fresh["provenance"])
    assert fresh["provenance"]["stale"] is False and fresh["provenance"]["data_as_of"] == fresh["fetched_at"]


def test_yield_provenance_reads_registry_and_interval(db: Session) -> None:
    db.add(ModelRegistry(name="yield_t_ha", version="3", stage="production", source="octopus", uri="x", features=[]))
    db.commit()
    row: Any = SimpleNamespace(model_name="yield_t_ha", model_version="3", p10=3.0, p90=5.0, created_at=NOW)
    fresh = yield_forecast.forecast_provenance(db, row, NOW, refreshed=True)
    assert_provenance(fresh)
    assert (fresh["source"], fresh["fallback_step"], fresh["stale"]) == ("octopus", 1, False)
    assert fresh["confidence"]["kind"] == "interval" and fresh["confidence"]["calibrated"] is False
    old = yield_forecast.forecast_provenance(db, row, NOW + timedelta(days=2), refreshed=False)
    assert old["stale"] is True
    bare: Any = SimpleNamespace(model_name="unknown", model_version="1", p10=None, p90=None, created_at=NOW)
    assert yield_forecast.forecast_provenance(db, bare, NOW, True)["confidence"]["kind"] == "none"


def test_assistant_chat_carries_provenance(client: TestClient, app: Any, world: World) -> None:
    install(app, response("end_turn", text("Bonjour.")))
    body = ask(client, world.farmer_a).json()["data"]
    assert_provenance(body["provenance"])
    assert body["provenance"]["model_name"] == "assistant_llm" and body["provenance"]["fallback_step"] == 0


# --- Chaîne de repli ---------------------------------------------------------------------------

class Engine:
    def __init__(self, name: str, result: Any = None, fail: bool = False) -> None:
        self.name, self.sources, self.result, self.fail, self.calls = name, (name,), result, fail, 0

    def predict(self, model_name: str, rows: Any) -> list[Any]:
        self.calls += 1
        if self.fail:
            raise InferenceError("panne")
        return self.result


def test_fallback_uses_first_working_backend() -> None:
    local, octopus = Engine("local", [1.0]), Engine("octopus", [2.0])
    result = predict_with_fallback([local, octopus], "m", [{}])
    assert (result.predictions, result.step, result.engine, result.used_fallback) == ([1.0], 0, "local", False)
    assert octopus.calls == 0


def test_fallback_moves_to_octopus_when_bundle_fails() -> None:
    result = predict_with_fallback([Engine("local", fail=True), Engine("octopus", [2.0])], "m", [{}])
    assert (result.step, result.engine, result.used_fallback) == (1, "octopus", True)


def test_fallback_ignores_missing_backend_and_uses_rules() -> None:
    result = predict_with_fallback([None, Engine("octopus", fail=True)], "m", [{}], rules=lambda rows: [9.0])
    assert (result.predictions, result.step, result.engine) == ([9.0], 2, "rules")


def test_fallback_without_any_answer_is_503() -> None:
    for backends in ([None], [Engine("local", fail=True)], []):
        with pytest.raises(AppError) as error:
            predict_with_fallback(backends, "m", [{}])
        assert error.value.code == "MODEL_UNAVAILABLE" and error.value.status == 503


def test_failing_rules_end_in_503() -> None:
    def broken(rows: Any) -> list[Any]:
        raise InferenceError("règles impossibles")

    with pytest.raises(AppError) as error:
        predict_with_fallback([None], "m", [{}], rules=broken)
    assert error.value.code == "MODEL_UNAVAILABLE"


# --- Mode hybride par service ------------------------------------------------------------------

def test_default_mode_follows_agri_mock() -> None:
    assert load_service_modes({}).default == REAL
    assert load_service_modes({"AGRI_MOCK": "1"}).default == MOCK
    assert load_service_modes({"AGRI_MOCK": "0"}).default == REAL


def test_overrides_apply_per_service_and_alias_is_accepted() -> None:
    modes = load_service_modes({"AGRI_MOCK": "1",
                                "AGRI_SERVICES": "irrigation_need=real, diagnosis_analyze=REAL,pest_risk=mock"})
    assert modes.is_real("irrigation_need") and modes.is_real("disease_diagnosis")
    assert modes.mode("pest_risk") == MOCK and modes.mode("weather") == MOCK
    assert modes.real_services() == ("irrigation_need", "disease_diagnosis")
    assert set(modes.as_dict()) == set(SERVICES) and len(SERVICES) == 18


@pytest.mark.parametrize("raw", ["irrigation_need", "irrigation_need=maybe", "nope=real", "=real"])
def test_invalid_overrides_are_rejected(raw: str) -> None:
    with pytest.raises(ServiceModeError):
        parse_overrides(raw)


def test_invalid_agri_services_stops_startup() -> None:
    with pytest.raises(ConfigError):
        load_settings({"APP_ENV": "test", "AGRI_SERVICES": "irigation_need=real"})
    settings = load_settings({"APP_ENV": "test", "AGRI_SERVICES": "irrigation_need=real", "AGRI_MOCK": "1"})
    assert settings.service_modes.is_real("irrigation_need") and not settings.service_modes.is_real("weather")

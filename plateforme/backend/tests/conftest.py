"""Fixtures communes : application sur SQLite mémoire (StaticPool), horloge figée, faux services."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_now
from app.core.config import Settings, load_settings
from app.core.security import hash_password
from app.db.models import Membership, Organization, User
from app.main import create_app

# Horloge figée au lancement de la suite : PyJWT vérifie l'expiration avec l'horloge réelle,
# une date fixe dans le passé rendrait tous les jetons expirés.
NOW = datetime.now(UTC).replace(second=0, microsecond=0)
PASSWORD = "mot-de-passe-de-test-1"
SERIAL_A = "SA92-000101"
SERIAL_B = "SA92-000202"
POLYGON = {
    "type": "Polygon",
    "coordinates": [[[-16.95, 15.13], [-16.94, 15.13], [-16.94, 15.14], [-16.95, 15.14], [-16.95, 15.13]]],
}
TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": "sqlite://",
    "JWT_SECRET": "s" * 48,
    "DEVICE_KEY_PEPPER": "p" * 48,
    "RATE_LIMIT_DEFAULT_PER_MIN": "100000",
    "RATE_LIMIT_AUTH_PER_MIN": "100000",
    "RATE_LIMIT_ASSISTANT_PER_MIN": "100000",
    "INFERENCE_BACKEND": "none",
    "ASSISTANT_MAX_ITERATIONS": "3",
}


class FakeWeather:
    """Fournisseur météo déterministe ; compte les appels pour vérifier le cache."""

    name = "fake"

    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    def daily_forecast(self, latitude: float, longitude: float, days: int) -> list[dict[str, Any]]:
        from app.services.weather import weather_unavailable

        self.calls += 1
        if self.fail:
            raise weather_unavailable()
        start = date(2026, 10, 20)
        return [{"date": (start + timedelta(days=i)).isoformat(), "t_max_c": 34.0, "t_min_c": 21.0,
                 "precipitation_mm": 0.0, "et0_mm": 5.5} for i in range(days)]


def make_settings(**overrides: str) -> Settings:
    return load_settings({**TEST_ENV, **overrides})


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings: Settings) -> Any:
    application = create_app(settings)
    application.dependency_overrides[get_now] = lambda: NOW
    application.state.weather_provider = FakeWeather()
    application.state.assistant_gateway = None
    application.state.assistant_gateway_ready = True
    return application


@pytest.fixture
def client(app: Any) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(app: Any) -> Iterator[Session]:
    session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def add_user(session: Session, org: Organization, role: str, email: str) -> User:
    user = User(email=email, password_hash=hash_password(PASSWORD), full_name=email.split("@")[0], locale="fr")
    session.add(user)
    session.flush()
    session.add(Membership(user_id=user.id, organization_id=org.id, role=role))
    session.commit()
    return user


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/v1/auth/token", json={"username": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


@dataclass(frozen=True)
class World:
    """Deux organisations : A (exploitation, parcelle, kit) et B (étrangère)."""

    org_a: uuid.UUID
    org_b: uuid.UUID
    admin_a: dict[str, str]
    farmer_a: dict[str, str]
    agronomist_a: dict[str, str]
    admin_b: dict[str, str]
    farm_id: str
    field_id: str
    device_id: str
    device_key: str


def _create_orgs(db: Session) -> tuple[Organization, Organization]:
    org_a = Organization(name="Coopérative A", kind="cooperative", region="Thiès")
    org_b = Organization(name="Coopérative B", kind="cooperative", region="Louga")
    db.add_all([org_a, org_b])
    db.commit()
    return org_a, org_b


@pytest.fixture
def world(client: TestClient, db: Session) -> World:
    org_a, org_b = _create_orgs(db)
    add_user(db, org_a, "admin", "admin@a.test")
    add_user(db, org_a, "farmer", "farmer@a.test")
    add_user(db, org_a, "agronomist", "agro@a.test")
    add_user(db, org_b, "admin", "admin@b.test")
    admin_a = login(client, "admin@a.test")
    farm = client.post("/v1/farms", headers=admin_a, json={
        "name": "Ferme de Mboro", "region": "Thiès", "commune": "Mboro", "latitude": 15.14, "longitude": -16.89,
        "area_ha": 2.0}).json()["data"]
    field = client.post(f"/v1/farms/{farm['id']}/fields", headers=admin_a, json={
        "name": "Parcelle 1", "area_ha": 0.5, "irrigation_type": "drip", "geometry": POLYGON}).json()["data"]
    device = client.post("/v1/devices", headers=admin_a, json={
        "serial": SERIAL_A, "name": "Kit 1", "field_id": field["id"]}).json()["data"]
    return World(org_a.id, org_b.id, admin_a, login(client, "farmer@a.test"), login(client, "agro@a.test"),
                 login(client, "admin@b.test"), farm["id"], field["id"], device["id"], device["device_key"])


def point(serial: str = SERIAL_A, ts: datetime | None = None, **metrics: Any) -> dict[str, Any]:
    """Point telemetry.v1 (champ `m`)."""
    when = ts or NOW - timedelta(minutes=5)
    return {"schema": "telemetry.v1", "device_id": serial, "ts": when.isoformat(), "fw": "1.1.0",
            "source": "relay", "m": metrics or {"soil_moisture_pct": 40.0}}

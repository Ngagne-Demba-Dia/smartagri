"""Jeu de démonstration (`app.seed`) : idempotence, portée RLS, clé du kit utilisable, CLI."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import seed as seed_module
from app.core.config import Settings
from app.db.models import CropCycle, Device, Equipment, Farm, Field, Membership, Organization, User
from app.db.session import RLS_KEY
from app.seed import DEMO_ORG, DEMO_SERIAL, seed
from tests.conftest import make_settings, point

COUNTED = (Organization, User, Membership, Farm, Field, CropCycle, Device, Equipment)


def _counts(db: Session) -> dict[str, int]:
    return {model.__name__: db.scalar(select(func.count()).select_from(model)) for model in COUNTED}


def test_seed_is_idempotent_and_scopes_tenant(client: TestClient, db: Session, settings: Settings) -> None:
    created = seed(db, settings)
    db.commit()
    assert created is not None and created.device_serial == DEMO_SERIAL
    org_id = db.scalars(select(Organization.id).where(Organization.name == DEMO_ORG)).one()
    assert db.info[RLS_KEY] == (org_id,)
    before = _counts(db)
    assert all(count == 1 for count in before.values()), before
    assert seed(db, settings) is None
    assert _counts(db) == before


def test_seeded_device_key_authenticates_telemetry(client: TestClient, db: Session, settings: Settings) -> None:
    created = seed(db, settings)
    db.commit()
    response = client.post("/v1/telemetry/batch", headers={"X-Device-Key": created.device_key},
                           json={"points": [point(serial=DEMO_SERIAL, soil_moisture_pct=38.0)]})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["accepted"] == 1


def test_main_refuses_production(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(seed_module, "get_settings", lambda: SimpleNamespace(app_env="prod"))
    assert seed_module.main([]) == 2
    assert "production" in capsys.readouterr().err


def test_main_creates_then_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    file_settings = make_settings(DATABASE_URL=f"sqlite:///{(tmp_path / 'seed.db').as_posix()}")
    monkeypatch.setattr(seed_module, "get_settings", lambda: file_settings)
    assert seed_module.main(["--create-schema"]) == 0
    assert "Clé du kit" in capsys.readouterr().out
    assert seed_module.main([]) == 0
    assert "déjà présente" in capsys.readouterr().out

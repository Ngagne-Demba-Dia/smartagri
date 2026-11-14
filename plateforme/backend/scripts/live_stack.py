"""Pile locale pour le test de contrat live (Sprint D1) : API réelle + base SQLite jetable + météo simulée.

    python -m scripts.live_stack --stack-file ../web/.live-stack.json [--port 8765] [--rain 6 --et0 16]

Démarre : (1) un faux fournisseur Open-Meteo en HTTP local (pluie et ET0 réglables, date du jour),
(2) l'API FastAPI réelle sur SQLite (données de démonstration de `app.seed`), (3) écrit le fichier `--stack-file`
(URL, identifiants) lu par `web/tests/live/`. Aucun secret réel : base temporaire, clés aléatoires, 127.0.0.1.
Ctrl+C pour arrêter ; la base temporaire est supprimée. Interdit hors développement (APP_ENV=local imposé).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import uvicorn

HOST = "127.0.0.1"


def weather_handler(rain_mm: float, et0_mm: float) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (API de http.server)
            days = int(parse_qs(urlparse(self.path).query).get("forecast_days", ["7"])[0])
            today = datetime.now(UTC).date()
            daily = {"time": [(today + timedelta(days=i)).isoformat() for i in range(days)],
                     "temperature_2m_max": [34.0] * days, "temperature_2m_min": [21.0] * days,
                     "precipitation_sum": [rain_mm] + [0.0] * (days - 1),
                     "et0_fao_evapotranspiration": [et0_mm] * days}
            body = json.dumps({"daily": daily}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # silence
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stack-file", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--weather-port", type=int, default=8766)
    parser.add_argument("--rain", type=float, default=6.0, help="pluie du jour (mm) annoncée par la météo simulée")
    parser.add_argument("--et0", type=float, default=16.0, help="ET0 du jour (mm) de la météo simulée")
    args = parser.parse_args()

    workdir = Path(tempfile.mkdtemp(prefix="agri-live-"))
    os.environ.update({
        "APP_ENV": "local", "DATABASE_URL": f"sqlite:///{(workdir / 'live.db').as_posix()}",
        "JWT_SECRET": secrets.token_hex(32), "DEVICE_KEY_PEPPER": secrets.token_hex(32),
        "INFERENCE_BACKEND": "none", "AUTO_CREATE_SCHEMA": "true", "METRICS_ENABLED": "false",
        "RATE_LIMIT_DEFAULT_PER_MIN": "100000", "RATE_LIMIT_AUTH_PER_MIN": "100000",
        "WEATHER_BASE_URL": f"http://{HOST}:{args.weather_port}/v1/forecast", "WEATHER_TIMEOUT_S": "5",
    })
    # Import tardif : la configuration est lue au moment de créer l'application.
    from fastapi import Depends, Request
    from fastapi.security import HTTPAuthorizationCredentials
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.api.deps import bearer_scheme, get_principal, get_session, get_settings as dep_settings, principal_from_credentials
    from app.core.config import Settings, get_settings
    from app.db.base import Base
    from app.db.models import Device, DeviceThreshold, Measurement, User
    from app.db.session import build_engine, build_session_factory, set_tenant_scope
    from app.main import create_app
    from app.seed import DEMO_ADMIN_EMAIL, DEMO_IDS, seed
    from app.services.access import DEMO_SLUG_TO_UUID, Principal

    for field_slug in ("fld-mboro-2", "fld-mboro-3", "fld-potou-1", "fld-potou-2", "fld-ndiol-1", "fld-ndiol-2"):
        DEMO_SLUG_TO_UUID.setdefault(field_slug, DEMO_IDS["fld-mboro-1"])
    for dev_slug in ("dev-0002", "dev-0003", "dev-0004", "dev-0101"):
        DEMO_SLUG_TO_UUID.setdefault(dev_slug, DEMO_IDS["dev-0001"])

    settings = get_settings()
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    with build_session_factory(engine)() as session:
        created = seed(session, settings)
        assert created is not None, "base jetable déjà peuplée ?"
        admin_user_id = session.scalar(select(User.id).where(User.email == DEMO_ADMIN_EMAIL))
        assert admin_user_id is not None
        device = session.get(Device, DEMO_IDS["dev-0001"])
        if device is not None:
            device.last_seen_at = now
            session.add(DeviceThreshold(
                device_id=device.id, organization_id=device.organization_id,
                desired_start_pct=28, desired_stop_pct=55,
                reported_start_pct=28, reported_stop_pct=55,
                sync_status="applied", updated_at=now,
            ))
            session.add(Measurement(
                device_id=device.id,
                ts=now - timedelta(minutes=10), received_at=now - timedelta(minutes=10),
                seq=1, source="http", soil_moisture_pct=24.0, air_temp_c=28.5, air_humidity_pct=65.0,
                n_mgkg=55, p_mgkg=22, k_mgkg=110, pump_on=False, pump_fault=False,
                soil_sensor_ok=True, bme_ok=True, npk_ok=True,
                threshold_start_pct=28, threshold_stop_pct=55,
            ))
        session.commit()

    weather = ThreadingHTTPServer((HOST, args.weather_port), weather_handler(args.rain, args.et0))
    threading.Thread(target=weather.serve_forever, daemon=True).start()
    args.stack_file.write_text(json.dumps({
        "api_url": f"http://{HOST}:{args.port}", "username": created.admin_login, "password": created.admin_password,
        "weather": {"rain_mm": args.rain, "et0_mm": args.et0},
    }), encoding="utf-8")

    app = create_app(settings)
    demo_org_id = DEMO_IDS["org-demo-niayes"]

    def hybrid_principal(
        request,
        session=Depends(get_session),
        cfg=Depends(dep_settings),
        credentials=Depends(bearer_scheme),
    ):
        if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials.startswith("mock-access-"):
            role = credentials.credentials.removeprefix("mock-access-")
            if role in ("admin", "agronomist", "coop_manager", "farmer"):
                principal = Principal.build(admin_user_id, {demo_org_id: role})
                set_tenant_scope(session, principal.org_ids)
                request.state.user_id = str(principal.user_id)
                return principal
        principal = principal_from_credentials(session, cfg, credentials)
        request.state.user_id = str(principal.user_id)
        return principal

    hybrid_principal.__annotations__ = {"request": Request, "return": Principal}
    app.dependency_overrides[get_principal] = hybrid_principal
    print(f"[live_stack] API FastAPI prete sur http://{HOST}:{args.port} (meteo simulee sur port {args.weather_port})", flush=True)
    try:
        uvicorn.run(app, host=HOST, port=args.port, log_level="info")
    finally:
        weather.shutdown()
        args.stack_file.unlink(missing_ok=True)
        engine.dispose()
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

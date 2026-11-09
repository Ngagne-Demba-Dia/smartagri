"""Dépendances FastAPI : réglages, session, utilisateur authentifié, horloge, pagination, moteurs injectables.

Les objets partagés (fabrique de sessions, fournisseur météo, passerelle Claude, moteur d'inférence)
vivent sur `app.state` : les tests les remplacent sans toucher au code des routes.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import unauthenticated
from app.core.security import hash_device_key
from app.db.models import Device
from app.db.session import session_scope, set_tenant_scope
from app.services import devices
from app.services.access import Principal
from app.services.assistant.gateway import AssistantGateway, build_gateway
from app.services.audit import RequestMeta
from app.services.auth import load_principal
from app.services.inference.base import ModelBackend
from app.services.inference.factory import build_backend
from app.services.weather import WeatherProvider

MAX_PAGE = 10_000
MAX_LIMIT = 200
DEFAULT_LIMIT = 50

bearer_scheme = HTTPBearer(auto_error=False, description="Jeton d'accès JWT")
_gateway_lock = threading.Lock()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)


def get_now() -> datetime:
    """Horloge UTC (remplacée dans les tests via `app.dependency_overrides`)."""
    return datetime.now(UTC)


def get_request_meta(request: Request) -> RequestMeta:
    client = request.client.host if request.client else None
    return RequestMeta(ip=client, request_id=getattr(request.state, "request_id", None))


def principal_from_credentials(session: Session, settings: Settings,
                               credentials: HTTPAuthorizationCredentials | None) -> Principal:
    """Utilisateur du jeton Bearer ; la session est ensuite restreinte à ses organisations (RLS)."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise unauthenticated()
    principal = load_principal(session, settings, credentials.credentials)
    set_tenant_scope(session, principal.org_ids)
    return principal


def get_principal(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    principal = principal_from_credentials(session, settings, credentials)
    request.state.user_id = str(principal.user_id)
    return principal


def device_from_key(session: Session, settings: Settings, device_key: str) -> Device | None:
    """Kit authentifié par X-Device-Key.

    Sous PostgreSQL (RLS forcée), l'organisation du kit est d'abord obtenue par la fonction
    SECURITY DEFINER `app_device_org_by_key` (001_init.sql), puis la session est restreinte à elle.
    """
    if not device_key or len(device_key) > 256:
        return None
    if session.get_bind().dialect.name == "postgresql":
        org_id = session.scalar(text("SELECT app_device_org_by_key(:key_hash)"),
                                {"key_hash": hash_device_key(settings, device_key)})
        if org_id is None:
            return None
        set_tenant_scope(session, [org_id])
    return devices.find_device_by_key(session, settings, device_key)


@dataclass(frozen=True)
class Pagination:
    page: int
    limit: int


def get_pagination(page: int = Query(1, ge=1, le=MAX_PAGE),
                   limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)) -> Pagination:
    return Pagination(page, limit)


def get_weather_provider(request: Request) -> WeatherProvider:
    return request.app.state.weather_provider


def get_assistant_gateway(request: Request) -> AssistantGateway | None:
    """Passerelle Claude construite au premier appel (import paresseux du SDK), puis réutilisée."""
    state = request.app.state
    if not getattr(state, "assistant_gateway_ready", False):
        with _gateway_lock:
            if not getattr(state, "assistant_gateway_ready", False):
                state.assistant_gateway = build_gateway(state.settings)
                state.assistant_gateway_ready = True
    return state.assistant_gateway


BackendFactory = Callable[[Settings, Session], ModelBackend | None]


def get_model_backend(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ModelBackend | None:
    factory: BackendFactory | Any = getattr(request.app.state, "model_backend_factory", None) or build_backend
    return factory(settings, session)

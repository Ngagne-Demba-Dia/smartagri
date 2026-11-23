"""Fabrique de l'application FastAPI SmartAgri92.

`uvicorn app.main:app` : l'attribut `app` est construit à la première lecture (PEP 562), ce qui
permet aux tests d'importer `create_app` sans lire l'environnement du processus.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1 import api_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.metrics import MetricsMiddleware
from app.core.middleware import BodySizeLimitMiddleware, RateLimitMiddleware, RateRule, RequestContextMiddleware
from app.db.base import Base
from app.db.session import build_engine, build_session_factory
from app.services import access
from app.services.inference.local_ai import SmartAgriAIClient, SmartAgriAITranscriber, SmartAgriAIVisionAnalyzer
from app.services.weather import build_provider

logger = logging.getLogger(__name__)
API_VERSION = "1.0.0"
MAX_BODY_BYTES = 2 * 1024 * 1024  # un lot de 1000 points tient largement dans 2 Mio


def _rate_rules(settings: Settings) -> tuple[RateRule, ...]:
    """Première règle dont le préfixe correspond : la plus spécifique d'abord."""
    return (
        RateRule("/v1/auth/token", settings.rate_limit_auth_per_min),
        RateRule("/v1/auth/refresh", settings.rate_limit_auth_per_min),
        RateRule("/v1/auth/logout", settings.rate_limit_auth_per_min),
        RateRule("/v1/assistant", settings.rate_limit_assistant_per_min),
        RateRule("/v1", settings.rate_limit_default_per_min),
    )


def _install_middleware(app: FastAPI, settings: Settings) -> None:
    # Starlette exécute en premier le dernier ajouté : RequestContext enveloppe tout le reste.
    app.add_middleware(RateLimitMiddleware, rules=_rate_rules(settings))
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_BODY_BYTES)
    if settings.metrics_enabled:
        app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Device-Key", "X-Request-ID"],
        allow_credentials=False,
    )
    app.add_middleware(RequestContextMiddleware)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construit l'application ; `settings` est injecté par les tests."""
    settings = settings or get_settings()
    if settings.app_env != "test":
        configure_logging()
    access.set_demo_slugs_enabled(not settings.is_strict)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            ai_client = getattr(application.state, "smartagri_ai_client", None)
            if ai_client is not None and hasattr(ai_client, "close"):
                ai_client.close()
            eng = getattr(application.state, "engine", None)
            if eng is not None and not settings.is_sqlite:
                eng.dispose()

    docs = settings.docs_enabled
    app = FastAPI(title="SmartAgri92 API", version=API_VERSION, docs_url="/docs" if docs else None,
                  redoc_url=None, openapi_url="/openapi.json" if docs else None, lifespan=lifespan)
    engine = build_engine(settings.database_url)
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.weather_provider = build_provider(settings)
    app.state.assistant_gateway = None
    app.state.assistant_gateway_ready = False
    app.state.model_backend_factory = None
    if settings.smartagri_ai_url:
        ai_cli = SmartAgriAIClient(
            settings.smartagri_ai_url,
            timeout_s=settings.smartagri_ai_timeout_s,
            api_key=settings.smartagri_ai_api_key,
        )
        app.state.smartagri_ai_client = ai_cli
        app.state.transcriber = SmartAgriAITranscriber(ai_cli)
        app.state.vision_analyzer = SmartAgriAIVisionAnalyzer(ai_cli)
    else:
        app.state.smartagri_ai_client = None
    install_error_handlers(app)
    _install_middleware(app, settings)
    app.include_router(health_router)
    app.include_router(api_router)
    logger.info("API prête (env=%s, base=%s)", settings.app_env, engine.dialect.name)
    logger.info("Modes des services (défaut=%s) : %s", settings.service_modes.default,
                ", ".join(f"{k}={v}" for k, v in settings.service_modes.as_dict().items()))
    return app


def __getattr__(name: str) -> Any:
    """Construit `app` paresseusement pour `uvicorn app.main:app`."""
    if name == "app":
        instance = create_app()
        globals()["app"] = instance
        return instance
    raise AttributeError(name)

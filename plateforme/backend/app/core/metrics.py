"""Métriques Prometheus optionnelles (`prometheus_client`).

Sans la bibliothèque, toutes les fonctions deviennent des no-op et `/metrics` n'est pas exposé.
En production, `/metrics` n'est joignable que depuis le réseau interne (NetworkPolicy).
"""

from __future__ import annotations

import importlib
import time
from collections.abc import Awaitable, Callable
from functools import lru_cache
from types import ModuleType
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@lru_cache(maxsize=1)
def _prometheus() -> ModuleType | None:
    try:
        return importlib.import_module("prometheus_client")
    except ImportError:
        return None


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any] | None:
    """Crée les collecteurs une seule fois par processus (évite les doublons d'enregistrement)."""
    prom = _prometheus()
    if prom is None:
        return None
    return {
        "requests": prom.Counter("agri_http_requests_total", "Requêtes HTTP", ["method", "route", "status"]),
        "latency": prom.Histogram("agri_http_request_seconds", "Durée des requêtes HTTP", ["method", "route"]),
        "telemetry": prom.Counter("agri_telemetry_points_total", "Points de télémétrie", ["outcome"]),
    }


def metrics_available() -> bool:
    return _registry() is not None


def count_telemetry(outcome: str, amount: int) -> None:
    registry = _registry()
    if registry is not None and amount > 0:
        registry["telemetry"].labels(outcome=outcome).inc(amount)


def render_metrics() -> tuple[bytes, str]:
    prom = _prometheus()
    if prom is None:
        return b"", "text/plain"
    return prom.generate_latest(), prom.CONTENT_TYPE_LATEST


class MetricsMiddleware(BaseHTTPMiddleware):
    """Compte les requêtes par gabarit de route (pas par URL brute : cardinalité bornée)."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        registry = _registry()
        start = time.perf_counter()
        response = await call_next(request)
        if registry is not None:
            route = request.scope.get("route")
            template = getattr(route, "path", "non_route")
            registry["requests"].labels(request.method, template, str(response.status_code)).inc()
            registry["latency"].labels(request.method, template).observe(time.perf_counter() - start)
        return response

"""Intergiciels HTTP : identifiant de requête, en-têtes de sécurité, limitation de débit.

La limitation de débit est en mémoire, par processus : suffisante pour le développement et un
pilote mono-réplique. En production (plusieurs répliques), la limite fait foi à l'ingress
(NGINX `limit_req`) ou via un compteur Redis partagé ; ce module reste une seconde barrière.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.envelope import fail

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9\-]{8,64}$")
WINDOW_SECONDS = 60.0

CallNext = Callable[[Request], Awaitable[Response]]


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Propage ou crée X-Request-ID et ajoute des en-têtes de sécurité à chaque réponse."""

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


@dataclass(frozen=True)
class RateRule:
    prefix: str
    per_minute: int


class SlidingWindowLimiter:
    """Fenêtre glissante d'une minute par (règle, client). Thread-safe avec purge périodique."""

    _PRUNE_EVERY = 256
    _MAX_KEYS = 4096

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()
        self._ops = 0

    def _prune(self, now: float) -> None:
        stale = [k for k, w in self._hits.items() if not w or now - w[-1] >= WINDOW_SECONDS]
        for k in stale:
            del self._hits[k]
        if len(self._hits) > self._MAX_KEYS:
            overflow = len(self._hits) - self._MAX_KEYS
            for k in list(self._hits)[:overflow]:
                del self._hits[k]

    def hit(self, rule: RateRule, client: str, now: float) -> float | None:
        """Enregistre un appel ; renvoie le délai d'attente (s) si la limite est atteinte."""
        key = (rule.prefix, client)
        with self._lock:
            self._ops += 1
            if self._ops >= self._PRUNE_EVERY or len(self._hits) > self._MAX_KEYS:
                self._prune(now)
                self._ops = 0
            window = self._hits.setdefault(key, deque())
            while window and now - window[0] >= WINDOW_SECONDS:
                window.popleft()
            if len(window) >= rule.per_minute:
                return max(1.0, WINDOW_SECONDS - (now - window[0]))
            window.append(now)
            return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applique la première règle dont le préfixe correspond au chemin."""

    def __init__(self, app: ASGIApp, rules: tuple[RateRule, ...]) -> None:
        super().__init__(app)
        self._rules = rules
        self._limiter = SlidingWindowLimiter()

    def _rule_for(self, path: str) -> RateRule | None:
        return next((rule for rule in self._rules if path.startswith(rule.prefix)), None)

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        rule = self._rule_for(request.url.path)
        if rule is None or rule.per_minute <= 0:
            return await call_next(request)
        client = request.client.host if request.client else "inconnu"
        retry_after = self._limiter.hit(rule, client, time.monotonic())
        if retry_after is not None:
            body = fail("RATE_LIMITED", "Trop de requêtes. Réessayez dans un instant.")
            return JSONResponse(body, status_code=429, headers={"Retry-After": str(int(retry_after))})
        return await call_next(request)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Refuse (413) une requête dont le corps dépasse la limite (Content-Length et chunked)."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            body = fail("PAYLOAD_TOO_LARGE", "Corps de requête trop volumineux.")
            return JSONResponse(body, status_code=413)
        if not declared and request.method in ("POST", "PUT", "PATCH"):
            raw = await request.body()
            if len(raw) > self._max_bytes:
                body = fail("PAYLOAD_TOO_LARGE", "Corps de requête trop volumineux.")
                return JSONResponse(body, status_code=413)
        return await call_next(request)

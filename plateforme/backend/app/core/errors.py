"""Erreurs métier et gestionnaires d'exceptions qui produisent toujours l'enveloppe standard."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.envelope import fail

logger = logging.getLogger(__name__)

HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    429: "RATE_LIMITED",
}
# Messages par défaut de Starlette (« Not Found »…) remplacés par des messages en français.
HTTP_MESSAGES = {
    401: "Authentification requise.",
    403: "Accès refusé.",
    404: "Ressource introuvable.",
    405: "Méthode non autorisée.",
}


class AppError(Exception):
    """Erreur prévue : code stable (pour les clients), message en français, statut HTTP."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        details: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = dict(details) if details else None
        self.headers = dict(headers) if headers else None


def not_found(resource: str = "Ressource") -> AppError:
    """404 générique : utilisé aussi pour les ressources d'une autre organisation (pas de fuite)."""
    return AppError("NOT_FOUND", f"{resource} introuvable.", 404)


def unauthenticated(message: str = "Authentification requise.", code: str = "UNAUTHENTICATED") -> AppError:
    return AppError(code, message, 401, headers={"WWW-Authenticate": "Bearer"})


def forbidden(message: str = "Action non autorisée pour votre rôle.") -> AppError:
    return AppError("FORBIDDEN", message, 403)


def _sanitize_validation(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retire les valeurs saisies (`input`) : elles peuvent contenir un mot de passe."""
    return [
        {"loc": [str(part) for part in err.get("loc", ())], "msg": err.get("msg", ""), "type": err.get("type", "")}
        for err in errors
    ]


async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(fail(exc.code, exc.message, exc.details), status_code=exc.status, headers=exc.headers)


async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = {"errors": _sanitize_validation(list(exc.errors()))}
    body = fail("VALIDATION_ERROR", "Requête invalide.", details)
    return JSONResponse(body, status_code=422)


async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
    message = HTTP_MESSAGES.get(exc.status_code) or (exc.detail if isinstance(exc.detail, str) else "Erreur HTTP.")
    headers = getattr(exc, "headers", None)
    return JSONResponse(fail(code, message), status_code=exc.status_code, headers=headers)


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Erreur interne non gérée", extra={"request_id": request_id})
    body = fail("INTERNAL_ERROR", "Erreur interne. Réessayez plus tard.", {"request_id": request_id})
    return JSONResponse(body, status_code=500)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)

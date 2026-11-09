"""Enveloppe de réponse unique : {success, data, error, meta} (CONVENTIONS §5)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class PageMeta(BaseModel):
    page: int
    limit: int
    total: int


class Envelope(BaseModel, Generic[T]):
    """Modèle OpenAPI de l'enveloppe ; les routes renvoient des dicts produits par `ok()`."""

    success: bool
    data: T | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any] | None = None


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": True, "data": data, "error": None, "meta": meta}


def fail(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"success": False, "data": None, "error": error, "meta": None}


def page_meta(page: int, limit: int, total: int) -> dict[str, int]:
    return {"page": page, "limit": limit, "total": total}

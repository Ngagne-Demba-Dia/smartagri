"""Passerelle vers l'API Claude (SDK `anthropic`, importé paresseusement).

Sans clé ANTHROPIC_API_KEY ou sans le paquet `anthropic`, `build_gateway` renvoie None et la route de
l'assistant répond 503 ASSISTANT_UNAVAILABLE ; le reste de la plateforme fonctionne normalement.

Syntaxe vérifiée dans la documentation du SDK (skill claude-api, shared/model-migration.md) :
- repli côté serveur : `client.beta.messages.create(..., betas=["server-side-fallback-2026-07-01"],
  fallbacks="default")` ; la forme tableau `fallbacks=[{"model": ...}]` exige l'en-tête `-2026-06-01`
  et mélanger les deux renvoie 400 ;
- réflexion adaptative `thinking={"type": "adaptive"}` et effort explicite `output_config={"effort": ...}` ;
  jamais `budget_tokens`, `temperature`, `top_p` ni `top_k` (rejetés en 400 par Claude Opus 5.5).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from app.core.config import Settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"
CLIENT_TIMEOUT_S = 60.0
CLIENT_MAX_RETRIES = 2

_BUSY = "L'assistant est très sollicité. Réessayez dans une minute."
_DOWN = "L'assistant est momentanément indisponible."
_UPSTREAM = "L'assistant a rencontré une erreur. Réessayez plus tard."

# Classe d'erreur du SDK -> (statut HTTP, code stable, message). Recherche dans l'ordre du MRO :
# la classe la plus spécifique l'emporte (APITimeoutError hérite d'APIConnectionError, etc.).
SDK_ERROR_MAP: dict[str, tuple[int, str, str]] = {
    "RateLimitError": (503, "ASSISTANT_RATE_LIMITED", _BUSY),
    "OverloadedError": (503, "ASSISTANT_OVERLOADED", _BUSY),
    "AuthenticationError": (503, "ASSISTANT_UNAVAILABLE", _DOWN),
    "PermissionDeniedError": (503, "ASSISTANT_UNAVAILABLE", _DOWN),
    "NotFoundError": (502, "ASSISTANT_MODEL_NOT_FOUND", _UPSTREAM),
    "BadRequestError": (502, "ASSISTANT_BAD_REQUEST", _UPSTREAM),
    "APITimeoutError": (503, "ASSISTANT_UNREACHABLE", _DOWN),
    "APIConnectionError": (503, "ASSISTANT_UNREACHABLE", _DOWN),
    "InternalServerError": (502, "ASSISTANT_UPSTREAM_ERROR", _UPSTREAM),
    "APIStatusError": (502, "ASSISTANT_UPSTREAM_ERROR", _UPSTREAM),
}


def assistant_unavailable() -> AppError:
    return AppError("ASSISTANT_UNAVAILABLE", "L'assistant n'est pas configuré sur cette plateforme.", 503)


def map_sdk_error(exc: BaseException) -> AppError | None:
    """Traduit une exception du SDK en AppError (None si l'exception ne vient pas du SDK)."""
    for cls in type(exc).__mro__:
        entry = SDK_ERROR_MAP.get(cls.__name__)
        if entry is not None:
            status, code, message = entry
            return AppError(code, message, status)
    return None


class AssistantGateway:
    """Enveloppe fine autour du client ; injectable (faux client) dans les tests."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def create(self, params: dict[str, Any]) -> Any:
        """Un appel Messages ; l'API bêta n'est utilisée que si des en-têtes bêta sont demandés."""
        try:
            if params.get("betas"):
                return self._client.beta.messages.create(**params)
            return self._client.messages.create(**params)
        except Exception as exc:
            mapped = map_sdk_error(exc)
            if mapped is None:
                raise
            logger.warning("Appel Claude en échec : %s -> %s", type(exc).__name__, mapped.code)
            raise mapped from exc


def build_gateway(settings: Settings) -> AssistantGateway | None:
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:
        logger.warning("Paquet « anthropic » absent : assistant désactivé (pip install .[assistant]).")
        return None
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=CLIENT_MAX_RETRIES,
                                 timeout=CLIENT_TIMEOUT_S)
    return AssistantGateway(client)


def build_params(settings: Settings, system_blocks: Sequence[dict[str, Any]], tools: Sequence[dict[str, Any]],
                 messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Paramètres de requête : réflexion adaptative, effort explicite, `tool_choice` auto, repli serveur."""
    params: dict[str, Any] = {
        "model": settings.assistant_model,
        "max_tokens": settings.assistant_max_tokens,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": settings.assistant_effort},
        "system": list(system_blocks),
        "tools": list(tools),
        "tool_choice": {"type": "auto"},
        "messages": list(messages),
    }
    if settings.assistant_server_fallback:
        params["betas"] = [FALLBACK_BETA]
        params["fallbacks"] = "default"
    return params


def fallback_used(response: Any) -> bool:
    """Vrai si un modèle de repli a servi la réponse (entrée `fallback_message` dans usage.iterations)."""
    usage = getattr(response, "usage", None)
    iterations = getattr(usage, "iterations", None) or []
    return any(getattr(entry, "type", None) == "fallback_message" for entry in iterations)


def echo_content(blocks: Sequence[Any]) -> list[Any]:
    """Contenu assistant à renvoyer au tour suivant.

    Après un repli en cours de génération, les blocs `thinking`, `redacted_thinking`, `tool_use` (et tout bloc
    interne inconnu) situés avant le dernier bloc `fallback` sont omis ; le bloc `fallback` est abandonné.
    """
    boundary = max((i for i, block in enumerate(blocks) if block.type == "fallback"), default=-1)
    if boundary < 0:
        return list(blocks)
    before = [block for block in blocks[:boundary] if block.type == "text"]
    return before + list(blocks[boundary + 1:])

"""Boucle de l'assistant : appel Claude, exécution des outils, gestion des arrêts, persistance.

Boucle manuelle (pas de tool runner) pour garder la main sur le contrôle d'accès de chaque outil, le
plafond d'itérations et la persistance. Tous les `tool_result` d'un tour partent dans UN seul message
utilisateur. Arrêts gérés : end_turn / stop_sequence (réponse), tool_use (outils), pause_turn (relance),
refusal (message neutre en français), max_tokens (réponse tronquée signalée).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.constants import LOCALES, ROLES
from app.core.errors import AppError, not_found
from app.db.models import Conversation, Message
from app.services import access
from app.services.provenance import provenance
from app.services.assistant.gateway import (
    AssistantGateway,
    assistant_unavailable,
    build_params,
    echo_content,
    fallback_used,
)
from app.services.assistant.prompts import LANGUAGE_QUALITY_NOTICE, system_blocks
from app.services.assistant.tools import ToolContext, execute_tool, tool_definitions

MAX_MESSAGE_CHARS = 2000
HISTORY_MESSAGES = 12
TITLE_CHARS = 80
REPLY_OFFSET = timedelta(microseconds=1)  # ordre stable question -> réponse dans l'historique
REFUSAL_REPLY = ("Je ne peux pas répondre à cette demande. Pour une question sur vos cultures, vos kits ou vos "
                 "alertes, reformulez-la ou contactez votre conseiller agricole.")
LIMIT_REPLY = ("J'ai consulté plusieurs sources sans pouvoir conclure. Précisez le kit ou la parcelle concernés, "
               "ou reformulez votre question.")
TRUNCATED_NOTICE = "\n\n(Réponse tronquée : posez une question plus précise pour une réponse complète.)"
EMPTY_REPLY = "Je n'ai pas de réponse à proposer pour le moment."


@dataclass(frozen=True)
class ChatRequest:
    message: str
    conversation_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    locale: str | None = None


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0

    def add(self, response: Any) -> Usage:
        usage = getattr(response, "usage", None)
        return Usage(
            self.input_tokens + (getattr(usage, "input_tokens", 0) or 0),
            self.output_tokens + (getattr(usage, "output_tokens", 0) or 0),
            self.cache_read_tokens + (getattr(usage, "cache_read_input_tokens", 0) or 0),
        )


@dataclass(frozen=True)
class LoopResult:
    reply: str
    stop_reason: str
    model: str | None
    tools_used: tuple[str, ...] = ()
    usage: Usage = field(default_factory=Usage)
    truncated: bool = False
    limit_reached: bool = False
    fallback_used: bool = False
    refusal_category: str | None = None


def _text_of(blocks: Sequence[Any]) -> str:
    return "\n".join(block.text for block in blocks if block.type == "text" and block.text).strip()


def _final_result(response: Any, content: Sequence[Any], base: LoopResult) -> LoopResult:
    stop = response.stop_reason or "end_turn"
    model = getattr(response, "model", base.model)
    if stop == "refusal":
        details = getattr(response, "stop_details", None)  # peut être null
        category = getattr(details, "category", None) if details is not None else None
        return replace(base, reply=REFUSAL_REPLY, stop_reason=stop, model=model, refusal_category=category)
    text = _text_of(content) or EMPTY_REPLY
    if stop == "max_tokens":
        return replace(base, reply=text + TRUNCATED_NOTICE, stop_reason=stop, model=model, truncated=True)
    return replace(base, reply=text, stop_reason=stop, model=model)


def _run_tools(ctx: ToolContext, content: Sequence[Any]) -> tuple[list[dict[str, Any]], list[str]]:
    results, names = [], []
    for block in content:
        if block.type != "tool_use":
            continue
        outcome = execute_tool(ctx, block.name, block.input)
        names.append(block.name)
        results.append({"type": "tool_result", "tool_use_id": block.id, "content": outcome.content,
                        "is_error": outcome.is_error})
    return results, names


def run_tool_loop(gateway: AssistantGateway, settings: Settings, ctx: ToolContext,
                  system: Sequence[dict[str, Any]], messages: Sequence[dict[str, Any]]) -> LoopResult:
    """Appels successifs jusqu'à une réponse finale ou le plafond `assistant_max_iterations`."""
    tools = tool_definitions()
    conversation = list(messages)
    state = LoopResult(reply="", stop_reason="", model=settings.assistant_model)
    for _ in range(settings.assistant_max_iterations):
        response = gateway.create(build_params(settings, system, tools, conversation))
        state = replace(state, usage=state.usage.add(response),
                        fallback_used=state.fallback_used or fallback_used(response))
        content = echo_content(response.content)
        if response.stop_reason == "pause_turn":
            conversation.append({"role": "assistant", "content": content})
            continue
        if response.stop_reason != "tool_use":
            return _final_result(response, content, state)
        results, names = _run_tools(ctx, content)
        state = replace(state, tools_used=state.tools_used + tuple(names))
        conversation.append({"role": "assistant", "content": content})
        if results:
            conversation.append({"role": "user", "content": results})
    return replace(state, reply=LIMIT_REPLY, stop_reason="iteration_limit", limit_reached=True)


def load_conversation(session: Session, principal: access.Principal, request: ChatRequest, locale: str,
                      now: datetime) -> Conversation:
    """Conversation existante de l'utilisateur (404 sinon) ou nouvelle conversation."""
    if request.conversation_id is not None:
        conversation = session.get(Conversation, request.conversation_id)
        if conversation is None or conversation.user_id != principal.user_id \
                or conversation.organization_id not in principal.roles_by_org:
            raise not_found("Conversation")
        return conversation
    org_id = access.resolve_org_for_write(principal, request.organization_id, ROLES)
    title = " ".join(request.message.split())[:TITLE_CHARS]
    conversation = Conversation(user_id=principal.user_id, organization_id=org_id, title=title, locale=locale,
                                created_at=now, updated_at=now)
    session.add(conversation)
    session.flush()
    return conversation


def history(session: Session, conversation_id: uuid.UUID) -> list[dict[str, Any]]:
    """Derniers échanges texte, commençant par un message utilisateur et alternés."""
    rows = session.scalars(
        select(Message).where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc()).limit(HISTORY_MESSAGES)
    ).all()
    turns: list[dict[str, Any]] = []
    for row in reversed(rows):
        if (not turns and row.role != "user") or (turns and turns[-1]["role"] == row.role):
            continue
        turns.append({"role": row.role, "content": row.content})
    if turns and turns[-1]["role"] == "user":
        turns.pop()
    return turns


def _persist(session: Session, conversation: Conversation, request: ChatRequest, result: LoopResult,
             now: datetime) -> None:
    session.add(Message(conversation_id=conversation.id, role="user", content=request.message, created_at=now))
    session.add(Message(
        conversation_id=conversation.id, role="assistant", content=result.reply, model=result.model,
        stop_reason=result.stop_reason, tools_used=list(result.tools_used),
        input_tokens=result.usage.input_tokens, output_tokens=result.usage.output_tokens,
        cache_read_tokens=result.usage.cache_read_tokens, created_at=now + REPLY_OFFSET,
    ))
    conversation.updated_at = now
    session.flush()


def _provenance(result: LoopResult, ctx: ToolContext) -> dict[str, Any]:
    """Provenance doc 16 § 9.2. L'enum gelée n'a pas de source « LLM externe » : `agriml` (plateforme)
    est la plus proche ; le modèle réellement utilisé est dans `model_version`. Repli 1 = autre modèle."""
    return provenance(model_name="assistant_llm", model_version=result.model or ctx.settings.assistant_model,
                      source="agriml", fallback_step=1 if result.fallback_used else 0, computed_at=ctx.now)


def _local_ai_reply(ctx: ToolContext, message: str, locale: str) -> LoopResult | None:
    """Repli local vers `smartagri-ai` (RAG + Orchestrateur) si aucune clé Anthropic n'est configurée."""
    if not ctx.settings.smartagri_ai_url:
        return None
    from app.services.inference.local_ai import SmartAgriAIClient

    cli = SmartAgriAIClient(ctx.settings.smartagri_ai_url, timeout_s=ctx.settings.smartagri_ai_timeout_s)
    query = message
    if locale == "wo":
        wo = cli.interpret_wolof(message)
        if wo and wo.get("normalized_fr"):
            query = str(wo["normalized_fr"])

    orch = cli.ask_orchestrator(query)
    rag = cli.search_knowledge(query, top_k=3)
    parts: list[str] = []
    tools: list[str] = []

    hits = []
    if rag and not rag.get("abstained"):
        hits = rag.get("values", {}).get("results", [])[:1]
    # Les extraits agronomiques (réponse lisible) passent en premier, avec leur source.
    for hit in hits:
        source = str(hit.get("doc_source", "RAG")).removeprefix("guide:").removesuffix(".md")
        parts.append(f"{hit.get('text_preview', '')}\n(Source : {source})")
    if hits:
        tools.append("smartagri_rag")
    # La synthèse de l'orchestrateur n'est ajoutée que si elle repose sur des données (pas d'abstention).
    answer = str(orch.get("answer", "")) if orch else ""
    if answer and not orch.get("abstentions") and not answer.startswith("Source RAG"):
        parts.append(f"Données de la parcelle : {answer}")
        tools.append("smartagri_orchestrator")

    if not parts:
        return None
    return LoopResult(
        reply="\n\n".join(parts),
        stop_reason="end_turn",
        model="smartagri-ai-local",
        tools_used=tuple(tools),
        fallback_used=True,
    )


def chat(gateway: AssistantGateway | None, ctx: ToolContext, request: ChatRequest,
         default_locale: str = "fr") -> dict[str, Any]:
    """Point d'entrée de POST /v1/assistant/chat (l'appelant valide la transaction)."""
    message = request.message.strip()
    if not message or len(message) > MAX_MESSAGE_CHARS:
        raise AppError("MESSAGE_INVALID", f"Message vide ou trop long ({MAX_MESSAGE_CHARS} caractères max).", 400)
    request = replace(request, message=message)
    locale = request.locale if request.locale in LOCALES else default_locale

    if gateway is None:
        local_result = _local_ai_reply(ctx, message, locale)
        if local_result is None:
            raise assistant_unavailable()
        conversation = load_conversation(ctx.session, ctx.principal, request, locale, ctx.now)
        _persist(ctx.session, conversation, request, local_result, ctx.now)
        return {"conversation_id": str(conversation.id), "reply": local_result.reply,
                "stop_reason": local_result.stop_reason, "tools_used": list(local_result.tools_used),
                "truncated": False, "limit_reached": False, "model": local_result.model,
                "fallback_used": True, "refusal_category": None,
                "language_quality_notice": LANGUAGE_QUALITY_NOTICE.get(locale),
                "provenance": _provenance(local_result, ctx)}

    conversation = load_conversation(ctx.session, ctx.principal, request, locale, ctx.now)
    messages = history(ctx.session, conversation.id) + [{"role": "user", "content": message}]
    system = system_blocks(ctx.now, locale, list(ctx.principal.roles_by_org.values()))
    result = run_tool_loop(gateway, ctx.settings, ctx, system, messages)
    _persist(ctx.session, conversation, request, result, ctx.now)
    return {"conversation_id": str(conversation.id), "reply": result.reply, "stop_reason": result.stop_reason,
            "tools_used": list(result.tools_used), "truncated": result.truncated,
            "limit_reached": result.limit_reached, "model": result.model, "fallback_used": result.fallback_used,
            "refusal_category": result.refusal_category,
            "language_quality_notice": LANGUAGE_QUALITY_NOTICE.get(locale),
            "provenance": _provenance(result, ctx)}

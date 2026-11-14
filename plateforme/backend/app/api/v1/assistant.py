"""Assistant agronomique (Claude) : conversation outillée, limitée aux données de l'utilisateur."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import (
    get_assistant_gateway,
    get_now,
    get_principal,
    get_request_meta,
    get_session,
    get_settings,
    get_weather_provider,
)
from app.core.config import Settings
from app.core.envelope import ok
from app.db.models import User
from app.schemas.assistant import ChatIn, TranscribeIn
from app.services.access import Principal
from app.services.assistant.gateway import AssistantGateway
from app.services.assistant.service import ChatRequest, chat
from app.services.assistant.tools import ToolContext
from app.services.assistant.transcribe import transcribe_audio
from app.services.audit import RequestMeta, record_audit
from app.services.weather import WeatherProvider

router = APIRouter(tags=["assistant"])


@router.post("/assistant/chat")
def assistant_chat(body: ChatIn, principal: Principal = Depends(get_principal),
                   session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
                   gateway: AssistantGateway | None = Depends(get_assistant_gateway),
                   provider: WeatherProvider = Depends(get_weather_provider), now: datetime = Depends(get_now),
                   meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    user = session.get(User, principal.user_id)
    ctx = ToolContext(session=session, settings=settings, principal=principal, now=now, weather_provider=provider)
    request = ChatRequest(message=body.message, conversation_id=body.conversation_id,
                          organization_id=body.organization_id, locale=body.locale)
    result = chat(gateway, ctx, request, default_locale=user.locale if user else "fr")
    # Audit sans le contenu des messages (données de l'utilisateur) : outils utilisés et issue seulement.
    record_audit(session, "assistant.chat", actor_user_id=principal.user_id, target_type="conversation",
                 target_id=result["conversation_id"], meta=meta,
                 details={"tools": result["tools_used"], "stop_reason": result["stop_reason"],
                          "fallback_used": result["fallback_used"]})
    session.commit()
    return ok(result)


@router.post("/assistant/transcribe")
def assistant_transcribe(body: TranscribeIn, request: Request, principal: Principal = Depends(get_principal),
                         session: Session = Depends(get_session), now: datetime = Depends(get_now),
                         meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    transcriber = getattr(request.app.state, "transcriber", None)
    result = transcribe_audio(
        audio_base64=body.audio_base64,
        content_type=body.content_type,
        duration_s=body.duration_s,
        language_hint=body.language_hint,
        now=now,
        transcriber=transcriber,
    )
    record_audit(session, "assistant.transcribe", actor_user_id=principal.user_id, target_type="audio",
                 target_id=None, meta=meta,
                 details={"language": result["language"], "duration_s": result["duration_s"]})
    session.commit()
    return ok(result)

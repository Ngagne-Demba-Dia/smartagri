"""Authentification : jeton d'accès + jeton de rafraîchissement à rotation, profil de l'utilisateur."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_now, get_principal, get_request_meta, get_session, get_settings
from app.core.config import Settings
from app.core.envelope import ok
from app.core.errors import AppError
from app.db.models import Membership, Organization, User
from app.schemas.auth import LoginIn, RefreshIn
from app.services import auth
from app.services.access import Principal
from app.services.audit import RequestMeta, record_audit

router = APIRouter(tags=["auth"])


@router.post("/auth/token")
def login(body: LoginIn, session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
          now: datetime = Depends(get_now), meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    try:
        user = auth.authenticate(session, body.username, body.password, now)
    except AppError:
        session.rollback()
        record_audit(session, "auth.login_failed", meta=meta)
        session.commit()
        raise
    pair, _ = auth.issue_tokens(session, settings, user.id, now)
    record_audit(session, "auth.login", actor_user_id=user.id, target_type="user", target_id=user.id, meta=meta)
    session.commit()
    return ok(asdict(pair))


@router.post("/auth/refresh")
def refresh(body: RefreshIn, session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
            now: datetime = Depends(get_now)) -> dict[str, Any]:
    pair = auth.rotate_refresh_token(session, settings, body.refresh_token, now)
    session.commit()
    return ok(asdict(pair))


@router.post("/auth/logout")
def logout(body: RefreshIn, session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
           now: datetime = Depends(get_now), meta: RequestMeta = Depends(get_request_meta)) -> dict[str, Any]:
    """Déconnexion : révoque la famille du jeton de rafraîchissement (rejouable sans erreur)."""
    user_id = auth.logout(session, settings, body.refresh_token, now)
    if user_id is not None:
        record_audit(session, "auth.logout", actor_user_id=user_id, target_type="user", target_id=user_id, meta=meta)
    session.commit()
    return ok({"logged_out": True})


@router.get("/me")
def me(principal: Principal = Depends(get_principal), session: Session = Depends(get_session)) -> dict[str, Any]:
    user = session.get(User, principal.user_id)
    rows = session.execute(
        select(Membership.role, Organization.id, Organization.name, Organization.kind)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == principal.user_id)
        .order_by(Organization.name)
    ).all()
    memberships = [{"organization_id": str(org_id), "organization_name": name, "organization_kind": kind,
                    "role": role} for role, org_id, name, kind in rows]
    return ok({"id": str(principal.user_id), "full_name": user.full_name if user else None,
               "email": user.email if user else None, "phone": user.phone if user else None,
               "locale": user.locale if user else "fr", "memberships": memberships})

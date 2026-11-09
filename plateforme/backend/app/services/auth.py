"""Authentification : connexion, rotation des jetons de rafraîchissement, chargement du principal.

Rotation avec détection de réutilisation : chaque jeton de rafraîchissement appartient à une famille.
Présenter un jeton déjà révoqué (vol probable) révoque toute la famille et force une reconnexion.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, unauthenticated
from app.core.security import (
    ACCESS,
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    dummy_password_check,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.db.base import as_utc
from app.db.models import Membership, RefreshToken, User
from app.services.access import Principal

INVALID_CREDENTIALS = "INVALID_CREDENTIALS"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


def normalize_login(username: str) -> tuple[str, str]:
    """('email', valeur en minuscules) ou ('phone', valeur sans espaces ni tirets)."""
    cleaned = username.strip()
    if "@" in cleaned:
        return "email", cleaned.lower()
    return "phone", cleaned.replace(" ", "").replace("-", "")


def find_user_by_login(session: Session, username: str) -> User | None:
    kind, value = normalize_login(username)
    column = User.email if kind == "email" else User.phone
    return session.scalars(select(User).where(column == value)).first()


def authenticate(session: Session, username: str, password: str, now: datetime) -> User:
    """Vérifie les identifiants ; même réponse (et même coût) si le compte n'existe pas."""
    user = find_user_by_login(session, username)
    if user is None:
        dummy_password_check(password)
        raise unauthenticated("Identifiants invalides.", INVALID_CREDENTIALS)
    if not verify_password(user.password_hash, password) or not user.is_active:
        raise unauthenticated("Identifiants invalides.", INVALID_CREDENTIALS)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = now
    return user


def issue_tokens(
    session: Session, settings: Settings, user_id: uuid.UUID, now: datetime, family_id: uuid.UUID | None = None
) -> tuple[TokenPair, RefreshToken]:
    """Émet un couple de jetons ; seule l'empreinte du jeton de rafraîchissement est stockée."""
    family = family_id or uuid.uuid4()
    access = create_access_token(settings, user_id, now)
    refresh = create_refresh_token(settings, user_id, family, now)
    row = RefreshToken(
        id=refresh.jti,
        user_id=user_id,
        family_id=family,
        token_hash=hash_token(refresh.token),
        expires_at=refresh.expires_at,
    )
    session.add(row)
    pair = TokenPair(access.token, refresh.token, settings.access_token_minutes * 60)
    return pair, row


def _revoke_family(session: Session, family_id: uuid.UUID, now: datetime) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )


def _load_refresh_row(session: Session, settings: Settings, token: str) -> RefreshToken:
    claims = decode_token(settings, token, REFRESH)
    try:
        jti = uuid.UUID(claims["jti"])
    except ValueError as exc:
        raise unauthenticated("Jeton invalide.", "TOKEN_INVALID") from exc
    row = session.get(RefreshToken, jti)
    if row is None or row.token_hash != hash_token(token) or str(row.user_id) != claims["sub"]:
        raise unauthenticated("Jeton invalide.", "TOKEN_INVALID")
    return row


def rotate_refresh_token(session: Session, settings: Settings, token: str, now: datetime) -> TokenPair:
    """Échange un jeton de rafraîchissement valide contre un nouveau couple (même famille).

    Réutilisation d'un jeton révoqué : la famille entière est révoquée et validée en base
    avant l'erreur 401, pour que la révocation survive au rollback de la requête.
    """
    row = _load_refresh_row(session, settings, token)
    if row.revoked_at is not None:
        _revoke_family(session, row.family_id, now)
        session.commit()
        raise unauthenticated("Jeton de rafraîchissement déjà utilisé : reconnectez-vous.", "REFRESH_TOKEN_REUSED")
    expires_at = as_utc(row.expires_at)
    if expires_at is not None and expires_at <= now:
        raise unauthenticated("Jeton expiré.", "TOKEN_EXPIRED")
    user = session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise unauthenticated("Compte désactivé.", "TOKEN_INVALID")
    pair, new_row = issue_tokens(session, settings, row.user_id, now, family_id=row.family_id)
    row.revoked_at = now
    row.replaced_by = new_row.id
    return pair


def logout(session: Session, settings: Settings, token: str, now: datetime) -> uuid.UUID | None:
    """Révoque la famille du jeton de rafraîchissement ; idempotent.

    Un jeton déjà révoqué ou expiré ne lève pas d'erreur (il est déjà inutilisable) ;
    un jeton falsifié reste une 401. Retourne l'utilisateur concerné, ou None si expiré.
    """
    try:
        row = _load_refresh_row(session, settings, token)
    except AppError as exc:
        if exc.code == "TOKEN_EXPIRED":
            return None
        raise
    _revoke_family(session, row.family_id, now)
    return row.user_id


def load_principal(session: Session, settings: Settings, access_token: str) -> Principal:
    """Décode le jeton d'accès et charge les rôles à jour (un retrait de rôle prend effet immédiatement)."""
    claims = decode_token(settings, access_token, ACCESS)
    try:
        user_id = uuid.UUID(claims["sub"])
    except ValueError as exc:
        raise unauthenticated("Jeton invalide.", "TOKEN_INVALID") from exc
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthenticated("Compte inconnu ou désactivé.", "TOKEN_INVALID")
    memberships = session.scalars(select(Membership).where(Membership.user_id == user_id)).all()
    return Principal.build(user_id, {m.organization_id: m.role for m in memberships})


def revoke_user_tokens(session: Session, user_id: uuid.UUID, now: datetime) -> None:
    """Révoque tous les jetons de rafraîchissement actifs d'un utilisateur (désactivation de compte)."""
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )

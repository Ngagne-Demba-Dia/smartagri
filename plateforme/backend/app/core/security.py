"""Primitives de sécurité : mots de passe (argon2id), jetons JWT, clés des kits.

- Mots de passe : argon2id (paramètres par défaut d'argon2-cffi, re-hachage si les paramètres évoluent).
- JWT HS256 : jeton d'accès 15 min, jeton de rafraîchissement 30 j, revendications iss/aud/exp/jti/type.
- Clés des kits : HMAC-SHA256 avec un poivre serveur. Le hachage est déterministe, ce qui permet de
  retrouver le kit par index ; la comparaison finale se fait en temps constant.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

from app.core.config import Settings
from app.core.errors import unauthenticated

ACCESS = "access"
REFRESH = "refresh"
JWT_ALGORITHM = "HS256"
DEVICE_KEY_BYTES = 32

_hasher = PasswordHasher()
# Hachage factice pour égaliser le temps de réponse quand l'utilisateur n'existe pas.
_DUMMY_HASH = _hasher.hash(secrets.token_hex(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def dummy_password_check(password: str) -> None:
    """Coût équivalent à une vérification réelle (anti-énumération des comptes)."""
    verify_password(_DUMMY_HASH, password)


@dataclass(frozen=True)
class IssuedToken:
    token: str
    jti: uuid.UUID
    expires_at: datetime


def _encode(settings: Settings, claims: dict[str, Any]) -> str:
    return jwt.encode(claims, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def _base_claims(settings: Settings, user_id: uuid.UUID, token_type: str, now: datetime, ttl: timedelta,
                 jti: uuid.UUID) -> dict[str, Any]:
    return {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": str(jti),
        "type": token_type,
    }


def create_access_token(settings: Settings, user_id: uuid.UUID, now: datetime) -> IssuedToken:
    ttl = timedelta(minutes=settings.access_token_minutes)
    jti = uuid.uuid4()
    token = _encode(settings, _base_claims(settings, user_id, ACCESS, now, ttl, jti))
    return IssuedToken(token=token, jti=jti, expires_at=now + ttl)


def create_refresh_token(settings: Settings, user_id: uuid.UUID, family_id: uuid.UUID, now: datetime) -> IssuedToken:
    ttl = timedelta(days=settings.refresh_token_days)
    jti = uuid.uuid4()
    claims = _base_claims(settings, user_id, REFRESH, now, ttl, jti) | {"fam": str(family_id)}
    return IssuedToken(token=_encode(settings, claims), jti=jti, expires_at=now + ttl)


def decode_token(settings: Settings, token: str, expected_type: str) -> dict[str, Any]:
    """Décode et vérifie un jeton ; toute anomalie donne une 401 sans détail exploitable."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "jti", "type", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise unauthenticated("Jeton expiré.", "TOKEN_EXPIRED") from exc
    except jwt.InvalidTokenError as exc:
        raise unauthenticated("Jeton invalide.", "TOKEN_INVALID") from exc
    if claims.get("type") != expected_type:
        raise unauthenticated("Type de jeton incorrect.", "TOKEN_INVALID")
    return claims


def hash_token(token: str) -> str:
    """Empreinte SHA-256 d'un jeton de rafraîchissement (seule l'empreinte est stockée)."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_device_key() -> str:
    return secrets.token_urlsafe(DEVICE_KEY_BYTES)


def hash_device_key(settings: Settings, device_key: str) -> str:
    return hmac.new(settings.device_key_pepper.encode(), device_key.encode(), hashlib.sha256).hexdigest()


def device_key_matches(settings: Settings, device_key: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_device_key(settings, device_key), stored_hash)

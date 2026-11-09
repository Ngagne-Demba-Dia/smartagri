"""Schémas d'authentification (corps JSON : python-multipart n'est pas requis)."""

from __future__ import annotations

from pydantic import Field

from app.schemas.common import InputModel


class LoginIn(InputModel):
    """Identifiant : adresse e-mail ou numéro de téléphone."""

    username: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class RefreshIn(InputModel):
    refresh_token: str = Field(min_length=20, max_length=4096)

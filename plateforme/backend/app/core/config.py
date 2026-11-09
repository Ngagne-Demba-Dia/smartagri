"""Configuration de l'application, lue une seule fois depuis l'environnement.

Les réglages sont immuables (dataclass gelée). En `staging` et `prod`, l'application refuse
de démarrer si un secret obligatoire manque ou est trop court (échec rapide).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache

logger = logging.getLogger(__name__)

VALID_ENVS = frozenset({"local", "test", "staging", "prod"})
STRICT_ENVS = frozenset({"staging", "prod"})
VALID_EFFORTS = frozenset({"low", "medium", "high"})
VALID_INFERENCE_BACKENDS = frozenset({"none", "local", "octopus"})
MIN_SECRET_BYTES = 32
DEFAULT_SQLITE_URL = "sqlite:///./agri_dev.db"


class ConfigError(RuntimeError):
    """Configuration invalide : l'application refuse de démarrer."""


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    database_url: str = DEFAULT_SQLITE_URL
    jwt_secret: str = ""
    jwt_issuer: str = "smartagri92-api"
    jwt_audience: str = "smartagri92"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    device_key_pepper: str = ""
    mqtt_url: str = "mqtt://localhost:1883"
    mqtt_username: str = ""
    mqtt_password: str = ""
    s3_endpoint: str = ""
    s3_bucket_raw: str = "agri-raw"
    anthropic_api_key: str = ""
    assistant_model: str = "claude-opus-5-5"
    assistant_effort: str = "medium"
    assistant_max_iterations: int = 6
    assistant_max_tokens: int = 8000
    assistant_server_fallback: bool = True
    weather_base_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_cache_minutes: int = 180
    weather_timeout_s: float = 10.0
    inference_backend: str = "local"
    model_bundle_dir: str = "./models"
    octopus_base_url: str = "https://octopus.ml"
    octopus_api_key: str = ""
    octopus_timeout_s: float = 60.0
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)
    rate_limit_default_per_min: int = 120
    rate_limit_auth_per_min: int = 10
    rate_limit_assistant_per_min: int = 20
    auto_create_schema: bool = False
    metrics_enabled: bool = True
    # Règles d'alerte (voir app/services/alerting.py)
    device_silent_hours: float = 24.0
    dry_soil_hours: float = 2.0
    disease_consecutive: int = 3
    disease_min_confidence: float = 0.7
    disease_window_hours: float = 48.0

    @property
    def is_strict(self) -> bool:
        return self.app_env in STRICT_ENVS

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def docs_enabled(self) -> bool:
        return self.app_env != "prod"


def _get(env: Mapping[str, str], key: str, default: str = "") -> str:
    return env.get(key, default).strip()


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = _get(env, key)
    try:
        return int(raw) if raw else default
    except ValueError as exc:
        raise ConfigError(f"{key} doit être un entier (reçu : {raw!r}).") from exc


def _float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = _get(env, key)
    try:
        return float(raw) if raw else default
    except ValueError as exc:
        raise ConfigError(f"{key} doit être un nombre (reçu : {raw!r}).") from exc


def _bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = _get(env, key).lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _csv(env: Mapping[str, str], key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = _get(env, key)
    if not raw:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _read_env(env: Mapping[str, str]) -> Settings:
    app_env = _get(env, "APP_ENV", "local") or "local"
    database_url = _get(env, "DATABASE_URL")
    sqlite_default = not database_url or database_url.startswith("sqlite")
    return Settings(
        app_env=app_env,
        database_url=database_url,
        jwt_secret=_get(env, "JWT_SECRET"),
        device_key_pepper=_get(env, "DEVICE_KEY_PEPPER"),
        mqtt_url=_get(env, "MQTT_URL", "mqtt://localhost:1883"),
        mqtt_username=_get(env, "MQTT_USERNAME"),
        mqtt_password=_get(env, "MQTT_PASSWORD"),
        s3_endpoint=_get(env, "S3_ENDPOINT"),
        s3_bucket_raw=_get(env, "S3_BUCKET_RAW", "agri-raw"),
        anthropic_api_key=_get(env, "ANTHROPIC_API_KEY"),
        assistant_model=_get(env, "ASSISTANT_MODEL", "claude-opus-5-5"),
        assistant_effort=_get(env, "ASSISTANT_EFFORT", "medium"),
        assistant_max_iterations=_int(env, "ASSISTANT_MAX_ITERATIONS", 6),
        assistant_server_fallback=_bool(env, "ASSISTANT_SERVER_FALLBACK", True),
        weather_base_url=_get(env, "WEATHER_BASE_URL", Settings.weather_base_url),
        weather_cache_minutes=_int(env, "WEATHER_CACHE_MINUTES", 180),
        weather_timeout_s=_float(env, "WEATHER_TIMEOUT_S", 10.0),
        inference_backend=_get(env, "INFERENCE_BACKEND", "local") or "local",
        model_bundle_dir=_get(env, "MODEL_BUNDLE_DIR", "./models") or "./models",
        octopus_base_url=_get(env, "OCTOPUS_BASE_URL", Settings.octopus_base_url) or Settings.octopus_base_url,
        octopus_api_key=_get(env, "OCTOPUS_API_KEY"),
        octopus_timeout_s=_float(env, "OCTOPUS_TIMEOUT_S", 60.0),
        cors_origins=_csv(env, "CORS_ORIGINS", Settings.cors_origins),
        rate_limit_default_per_min=_int(env, "RATE_LIMIT_DEFAULT_PER_MIN", 120),
        rate_limit_auth_per_min=_int(env, "RATE_LIMIT_AUTH_PER_MIN", 10),
        rate_limit_assistant_per_min=_int(env, "RATE_LIMIT_ASSISTANT_PER_MIN", 20),
        auto_create_schema=_bool(env, "AUTO_CREATE_SCHEMA", sqlite_default),
        metrics_enabled=_bool(env, "METRICS_ENABLED", True),
        device_silent_hours=_float(env, "DEVICE_SILENT_HOURS", 24.0),
        dry_soil_hours=_float(env, "DRY_SOIL_HOURS", 2.0),
        disease_consecutive=_int(env, "DISEASE_CONSECUTIVE", 3),
        disease_min_confidence=_float(env, "DISEASE_MIN_CONFIDENCE", 0.7),
        disease_window_hours=_float(env, "DISEASE_WINDOW_HOURS", 48.0),
    )


def _derive_pepper(jwt_secret: str) -> str:
    """Poivre de développement dérivé du secret JWT (jamais utilisé en staging/prod)."""
    return hmac.new(jwt_secret.encode(), b"device-key-pepper", hashlib.sha256).hexdigest()


def finalize(settings: Settings) -> Settings:
    """Valide les réglages ; complète les secrets manquants hors production."""
    if settings.app_env not in VALID_ENVS:
        raise ConfigError(f"APP_ENV inconnu : {settings.app_env!r}.")
    if settings.assistant_effort not in VALID_EFFORTS:
        raise ConfigError("ASSISTANT_EFFORT doit valoir low, medium ou high.")
    if settings.inference_backend not in VALID_INFERENCE_BACKENDS:
        raise ConfigError("INFERENCE_BACKEND doit valoir none, local ou octopus.")
    if not settings.octopus_base_url.startswith("https://") and settings.is_strict:
        raise ConfigError("OCTOPUS_BASE_URL doit être en HTTPS en staging/prod.")
    if settings.is_strict:
        return _validate_strict(settings)
    updated = settings
    if not updated.database_url:
        updated = replace(updated, database_url=DEFAULT_SQLITE_URL)
    if len(updated.jwt_secret.encode()) < MIN_SECRET_BYTES:
        logger.warning("JWT_SECRET absent ou court : secret aléatoire généré (jetons perdus au redémarrage).")
        updated = replace(updated, jwt_secret=secrets.token_hex(32))
    if not updated.device_key_pepper:
        updated = replace(updated, device_key_pepper=_derive_pepper(updated.jwt_secret))
    return updated


def _validate_strict(settings: Settings) -> Settings:
    if not settings.database_url:
        raise ConfigError("DATABASE_URL est obligatoire en staging/prod.")
    if settings.is_sqlite:
        raise ConfigError("SQLite est interdit en staging/prod : utiliser PostgreSQL/TimescaleDB.")
    if len(settings.jwt_secret.encode()) < MIN_SECRET_BYTES:
        raise ConfigError("JWT_SECRET doit faire au moins 32 octets en staging/prod.")
    if len(settings.device_key_pepper.encode()) < MIN_SECRET_BYTES:
        raise ConfigError("DEVICE_KEY_PEPPER doit faire au moins 32 octets en staging/prod.")
    return replace(settings, auto_create_schema=False)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Lit et valide la configuration (par défaut depuis os.environ)."""
    return finalize(_read_env(os.environ if env is None else env))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Réglages du processus, calculés une seule fois."""
    return load_settings()

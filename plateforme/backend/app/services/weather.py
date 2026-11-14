"""Prévisions météo quotidiennes : adaptateur fournisseur, cache en base et ET0 de Hargreaves.

Le fournisseur par défaut suit l'API Open-Meteo (`/v1/forecast`, variables quotidiennes). L'URL de base vient
de la configuration (WEATHER_BASE_URL), jamais de la requête : pas de SSRF possible. Attention : l'usage
commercial d'Open-Meteo exige un abonnement ; un autre fournisseur s'ajoute en implémentant `WeatherProvider`.

Si le fournisseur est injoignable, une réponse en cache périmée est servie (marquée `stale`) plutôt qu'une
erreur ; sans cache, l'appel échoue en 503 WEATHER_UNAVAILABLE.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.db.base import as_utc
from app.db.models import WeatherCache
from app.services import agronomy
from app.services.provenance import rules_provenance

logger = logging.getLogger(__name__)

MAX_FORECAST_DAYS = 16
COORD_DECIMALS = 2
DAILY_VARIABLES = ("temperature_2m_max", "temperature_2m_min", "precipitation_sum", "et0_fao_evapotranspiration")
ROW_KEYS = ("t_max_c", "t_min_c", "precipitation_mm", "et0_mm")


def weather_unavailable(reason: str = "Service météo indisponible.") -> AppError:
    return AppError("WEATHER_UNAVAILABLE", reason, 503)


@dataclass(frozen=True)
class DailyWeather:
    date: str
    t_max_c: float | None
    t_min_c: float | None
    precipitation_mm: float | None
    et0_mm: float | None
    et0_hargreaves_mm: float | None


@dataclass(frozen=True)
class Forecast:
    provider: str
    latitude: float
    longitude: float
    fetched_at: datetime
    source: str  # provider | cache | stale_cache
    days: tuple[DailyWeather, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"provider": self.provider, "latitude": self.latitude, "longitude": self.longitude,
                "fetched_at": self.fetched_at.isoformat(), "source": self.source,
                "days": [asdict(day) for day in self.days]}


def weather_provenance(forecast: Forecast, now: datetime) -> dict[str, Any]:
    """Provenance doc 16 § 9.2. Une prévision brute d'un fournisseur n'est pas un modèle AgriML : la source
    la plus proche de l'enum gelée est `rules` (repli 2). `stale` = servie depuis un cache périmé."""
    return rules_provenance(forecast.provider or "weather-provider", "v1", now,
                            data_as_of=forecast.fetched_at, stale=forecast.source == "stale_cache")


class WeatherProvider(Protocol):
    name: str

    def daily_forecast(self, latitude: float, longitude: float, days: int) -> list[dict[str, Any]]:
        """Lignes {date, t_max_c, t_min_c, precipitation_mm, et0_mm} ; lève AppError 503 en cas d'échec."""
        ...


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise weather_unavailable("Réponse météo invalide (valeur non numérique).")
    return float(value)


def parse_open_meteo(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Convertit le bloc `daily` d'Open-Meteo en lignes ; refuse une réponse incohérente."""
    daily = payload.get("daily") if isinstance(payload, Mapping) else None
    if not isinstance(daily, Mapping) or not isinstance(daily.get("time"), list):
        raise weather_unavailable("Réponse météo invalide (bloc « daily » absent).")
    dates = daily["time"]
    columns = [daily.get(name) for name in DAILY_VARIABLES]
    if any(not isinstance(col, list) or len(col) != len(dates) for col in columns):
        raise weather_unavailable("Réponse météo invalide (séries de longueurs différentes).")
    rows = []
    for index, day in enumerate(dates):
        values = {key: _optional_number(col[index]) for key, col in zip(ROW_KEYS, columns, strict=True)}
        rows.append({"date": str(day), **values})
    return rows


class OpenMeteoProvider:
    """Client HTTP minimal (httpx) ; `client` est injectable pour les tests (httpx.MockTransport)."""

    name = "open-meteo"

    def __init__(self, base_url: str, timeout_s: float = 10.0, client: httpx.Client | None = None) -> None:
        self._base_url = base_url
        self._timeout = httpx.Timeout(timeout_s, connect=min(timeout_s, 5.0))
        self._client = client

    def daily_forecast(self, latitude: float, longitude: float, days: int) -> list[dict[str, Any]]:
        params = {"latitude": latitude, "longitude": longitude, "daily": ",".join(DAILY_VARIABLES),
                  "timezone": "Africa/Dakar", "forecast_days": days}
        try:
            if self._client is not None:
                response = self._client.get(self._base_url, params=params, timeout=self._timeout)
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.get(self._base_url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Fournisseur météo en échec : %s", type(exc).__name__)
            raise weather_unavailable() from exc
        return parse_open_meteo(payload)


def _hargreaves(row: Mapping[str, Any], latitude: float) -> float | None:
    t_max, t_min = row.get("t_max_c"), row.get("t_min_c")
    if t_max is None or t_min is None or t_max < t_min:
        return None
    try:
        day_of_year = date.fromisoformat(row["date"]).timetuple().tm_yday
    except (KeyError, ValueError):
        return None
    ra = agronomy.extraterrestrial_radiation(latitude, day_of_year)
    return round(agronomy.hargreaves_et0(t_max, t_min, ra), 2)


def enrich_rows(rows: Sequence[Mapping[str, Any]], latitude: float) -> tuple[DailyWeather, ...]:
    """Ajoute l'ET0 de Hargreaves (FAO-56 éq. 52) calculée par la plateforme à côté de celle du fournisseur."""
    return tuple(
        DailyWeather(date=str(row.get("date")), t_max_c=row.get("t_max_c"), t_min_c=row.get("t_min_c"),
                     precipitation_mm=row.get("precipitation_mm"), et0_mm=row.get("et0_mm"),
                     et0_hargreaves_mm=_hargreaves(row, latitude))
        for row in rows
    )


def _cache_row(session: Session, provider: str, lat: float, lon: float, days: int) -> WeatherCache | None:
    return session.scalars(
        select(WeatherCache).where(WeatherCache.provider == provider, WeatherCache.latitude == lat,
                                   WeatherCache.longitude == lon, WeatherCache.days == days)
    ).first()


def _store(session: Session, cached: WeatherCache | None, key: tuple[str, float, float, int],
           rows: list[dict[str, Any]], now: datetime) -> None:
    if cached is not None:
        cached.fetched_at = now
        cached.payload = {"rows": rows}
        session.flush()
        return
    provider, lat, lon, days = key
    try:
        with session.begin_nested():
            session.add(WeatherCache(provider=provider, latitude=lat, longitude=lon, days=days, fetched_at=now,
                                     payload={"rows": rows}))
            session.flush()
    except IntegrityError:
        existing = _cache_row(session, provider, lat, lon, days)
        if existing is not None:
            existing.fetched_at = now
            existing.payload = {"rows": rows}
            session.flush()


def forecast_with_cache(session: Session, provider: WeatherProvider, latitude: float, longitude: float,
                        days: int, now: datetime, ttl: timedelta) -> Forecast:
    """Prévision quotidienne avec cache (clé : fournisseur, point arrondi à 0,01°, horizon)."""
    if not 1 <= days <= MAX_FORECAST_DAYS:
        raise AppError("INVALID_DAYS", f"« days » doit être compris entre 1 et {MAX_FORECAST_DAYS}.", 400)
    lat, lon = round(latitude, COORD_DECIMALS), round(longitude, COORD_DECIMALS)
    cached = _cache_row(session, provider.name, lat, lon, days)
    fetched_at = as_utc(cached.fetched_at) if cached else None
    if cached is not None and fetched_at is not None and now - fetched_at < ttl:
        return Forecast(provider.name, lat, lon, fetched_at, "cache", enrich_rows(cached.payload["rows"], lat))
    try:
        rows = provider.daily_forecast(lat, lon, days)
    except AppError:
        if cached is None or fetched_at is None:
            raise
        return Forecast(provider.name, lat, lon, fetched_at, "stale_cache", enrich_rows(cached.payload["rows"], lat))
    _store(session, cached, (provider.name, lat, lon, days), rows, now)
    return Forecast(provider.name, lat, lon, now, "provider", enrich_rows(rows, lat))


def build_provider(settings: Settings) -> WeatherProvider:
    """Fournisseur configuré (Open-Meteo par défaut) ; URL et délai issus de la configuration uniquement."""
    return OpenMeteoProvider(settings.weather_base_url, settings.weather_timeout_s)

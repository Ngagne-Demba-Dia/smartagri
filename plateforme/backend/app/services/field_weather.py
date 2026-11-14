"""Signal météo d'une parcelle pour les moteurs agronomiques : prévision en cache, jamais bloquante.

Contrairement à la route `/weather` (503 si le fournisseur et le cache échouent), un moteur d'irrigation doit
continuer à répondre sans météo : l'absence de prévision se traduit par `None`, pas par une erreur.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import Field
from app.services import farms, weather
from app.services.weather import DailyWeather, Forecast, WeatherProvider

logger = logging.getLogger(__name__)

# Même horizon que la route `/weather` par défaut : les deux appels partagent la ligne de cache.
SIGNAL_FORECAST_DAYS = 7


def field_forecast(session: Session, field: Field, provider: WeatherProvider, settings: Settings,
                   now: datetime) -> Forecast | None:
    """Prévision de la parcelle ; None sans localisation ou si la météo est indisponible (cache compris)."""
    location = farms.field_location(session, field)
    if location is None:
        return None
    ttl = timedelta(minutes=settings.weather_cache_minutes)
    try:
        return weather.forecast_with_cache(session, provider, location.latitude, location.longitude,
                                           SIGNAL_FORECAST_DAYS, now, ttl)
    except AppError as exc:
        if exc.code != "WEATHER_UNAVAILABLE":
            raise
        logger.warning("Météo indisponible pour la parcelle %s : signal de pluie ignoré", field.id)
        return None


def today_row(forecast: Forecast | None, now: datetime) -> DailyWeather | None:
    """Ligne du jour courant (date UTC = date Africa/Dakar) ; à défaut la première ligne à venir."""
    if forecast is None:
        return None
    today = now.date().isoformat()
    upcoming = [day for day in forecast.days if day.date >= today]
    return min(upcoming, key=lambda day: day.date) if upcoming else None

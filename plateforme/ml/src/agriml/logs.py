"""Configuration commune des journaux pour les interfaces en ligne de commande."""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s | %(message)s"


def setup_logging(level: str = "INFO") -> None:
    """Journaux lisibles ; force l'UTF-8 sur la console (Windows cp1252 ne sait pas écrire « → », « ≥ »…)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=level.upper(), format=LOG_FORMAT)

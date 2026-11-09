"""Tâche périodique : alertes « kit muet » (aucune donnée depuis DEVICE_SILENT_HOURS).

Usage : `python -m app.jobs.alert_sweep [--once] [--interval 900]`.
En production, la tâche tourne avec le rôle `agri_worker` (BYPASSRLS) : elle couvre toutes les organisations.
"""

from __future__ import annotations

import argparse
import logging
import signal
import threading
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import build_engine, build_session_factory
from app.services import alerting

logger = logging.getLogger(__name__)
DEFAULT_INTERVAL_S = 900


def run_once(factory: sessionmaker[Session], settings: Settings, now: datetime | None = None) -> int:
    """Un passage complet ; renvoie le nombre d'alertes créées."""
    with factory() as session:
        try:
            raised = alerting.sweep_silent_devices(session, settings, now or datetime.now(UTC))
            session.commit()
        except Exception:
            session.rollback()
            raise
    logger.info("Balayage des kits muets : %d alerte(s) créée(s)", raised)
    return raised


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Balayage périodique des kits muets.")
    parser.add_argument("--once", action="store_true", help="un seul passage puis sortie")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_S, help="secondes entre deux passages")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = get_settings()
    configure_logging()
    factory = build_session_factory(build_engine(settings.database_url))
    if args.once:
        run_once(factory, settings)
        return 0
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    while not stop.is_set():
        try:
            run_once(factory, settings)
        except Exception:
            # Une erreur transitoire (base indisponible) ne doit pas arrêter la boucle.
            logger.exception("Échec du balayage ; nouvel essai au prochain intervalle")
        stop.wait(max(60, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

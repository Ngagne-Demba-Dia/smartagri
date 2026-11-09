"""Moteur, sessions et portée multi-organisation (RLS PostgreSQL).

Sous PostgreSQL, chaque transaction positionne `app.org_id` (liste d'UUID séparés par des virgules)
à partir de `session.info["rls_org_ids"]` ; les politiques RLS de `001_init.sql` filtrent alors les
lignes. L'API filtre aussi explicitement par organisation : la RLS est une défense en profondeur.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

RLS_KEY = "rls_org_ids"


def _is_memory_sqlite(url: str) -> bool:
    return url.startswith("sqlite") and (":memory:" in url or url.rstrip("/") in {"sqlite:", "sqlite://"})


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine(url: str, echo: bool = False) -> Engine:
    """Crée le moteur ; SQLite mémoire partage une connexion unique (StaticPool) pour les tests."""
    if url.startswith("sqlite"):
        kwargs: dict[str, Any] = {"connect_args": {"check_same_thread": False}}
        if _is_memory_sqlite(url):
            kwargs["poolclass"] = StaticPool
        engine = create_engine(url, echo=echo, **kwargs)
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(url, echo=echo, pool_pre_ping=True, pool_size=10, max_overflow=10)


def _apply_rls_scope(session: Session, _transaction: Any, connection: Any) -> None:
    if connection.dialect.name != "postgresql":
        return
    org_ids = session.info.get(RLS_KEY)
    if org_ids is None:
        return
    value = ",".join(str(org_id) for org_id in org_ids)
    connection.execute(text("SELECT set_config('app.org_id', :value, true)"), {"value": value})


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    event.listen(factory, "after_begin", _apply_rls_scope)
    return factory


def set_tenant_scope(session: Session, org_ids: Iterable[UUID]) -> None:
    """Restreint la session aux organisations données (prend effet à la prochaine transaction)."""
    session.info[RLS_KEY] = tuple(org_ids)
    if session.in_transaction() and session.get_bind().dialect.name == "postgresql":
        value = ",".join(str(org_id) for org_id in session.info[RLS_KEY])
        session.execute(text("SELECT set_config('app.org_id', :value, true)"), {"value": value})


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Générateur de session pour les dépendances FastAPI : rollback si une exception remonte."""
    session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

"""Exécuteur des migrations SQL : ``python -m app.db.migrate [--dry-run] [--dir DOSSIER]``.

Applique ``$MIGRATIONS_DIR/*.sql`` (défaut ``/app/migrations``) dans l'ordre lexical et
inscrit chaque fichier dans ``schema_migrations(version, sha256, applied_at)``.

- Verrou consultatif ``pg_advisory_lock`` tenu pendant toute l'exécution (une seule
  instance à la fois, ex. Job migrate relancé).
- Autocommit, une instruction à la fois : les agrégats continus TimescaleDB refusent de
  s'exécuter dans un bloc de transaction ou une chaîne multi-instructions.
- Un fichier déjà appliqué dont l'empreinte a changé arrête tout (code de sortie 1).
- Une migration interrompue n'est pas inscrite : elle sera rejouée au prochain passage,
  d'où l'obligation d'écrire des migrations rejouables (IF NOT EXISTS, DROP ... IF EXISTS).

Connexion : ``MIGRATION_DATABASE_URL`` (rôle propriétaire) sinon ``DATABASE_URL``.
La planification, les empreintes et le découpage SQL sont des fonctions pures, testées
sans base de données ; seul ``PsycopgDatabase`` parle à PostgreSQL (psycopg importé à la demande).
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

DEFAULT_MIGRATIONS_DIR = "/app/migrations"
# Clé arbitraire mais fixe du verrou consultatif (« SA92 » + 1).
ADVISORY_LOCK_KEY = 0x5341_3932_0001
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

SCHEMA_MIGRATIONS_DDL = (
    "CREATE TABLE IF NOT EXISTS schema_migrations ("
    "version text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())"
)
DOLLAR_TAG_RE = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


class MigrationError(Exception):
    """Échec attendu (configuration, connexion, SQL) : message en français, sortie non nulle."""


@dataclass(frozen=True)
class MigrationFile:
    version: str
    sql: str
    sha256: str


@dataclass(frozen=True)
class MigrationPlan:
    pending: tuple[MigrationFile, ...]
    changed: tuple[str, ...]
    unknown: tuple[str, ...]


class MigrationDatabase(Protocol):
    def lock(self) -> None: ...
    def unlock(self) -> None: ...
    def ensure_table(self) -> None: ...
    def applied(self) -> dict[str, str]: ...
    def execute(self, statement: str) -> None: ...
    def record(self, version: str, sha256: str) -> None: ...


# --- Fonctions pures ---------------------------------------------------------------------------

def checksum(sql: str) -> str:
    """SHA-256 du contenu, fins de ligne normalisées (une extraction CRLF sous Windows
    ne doit pas faire croire à une migration modifiée)."""
    normalized = sql.replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def migration_file(name: str, sql: str) -> MigrationFile:
    return MigrationFile(version=Path(name).stem, sql=sql, sha256=checksum(sql))


def discover(directory: Path) -> tuple[MigrationFile, ...]:
    """Fichiers ``*.sql`` du dossier, triés par nom (ordre lexical)."""
    if not directory.is_dir():
        raise MigrationError(f"Dossier de migrations introuvable : {directory}")
    paths = sorted(directory.glob("*.sql"), key=lambda path: path.name)
    if not paths:
        raise MigrationError(f"Aucun fichier .sql dans {directory}")
    return tuple(migration_file(path.name, path.read_text(encoding="utf-8")) for path in paths)


def plan(files: Sequence[MigrationFile], applied: Mapping[str, str]) -> MigrationPlan:
    """Compare les fichiers aux versions inscrites : à appliquer, modifiées, inconnues."""
    on_disk = {item.version for item in files}
    pending = tuple(item for item in files if item.version not in applied)
    changed = tuple(item.version for item in files
                    if item.version in applied and applied[item.version] != item.sha256)
    unknown = tuple(sorted(version for version in applied if version not in on_disk))
    return MigrationPlan(pending=pending, changed=changed, unknown=unknown)


def _quoted_end(sql: str, start: int, quote: str) -> int:
    """Fin d'une chaîne '...' ou d'un identifiant "..." (guillemet doublé = échappement)."""
    index = start + 1
    while index < len(sql):
        if sql[index] == quote:
            if index + 1 < len(sql) and sql[index + 1] == quote:
                index += 2
                continue
            return index + 1
        index += 1
    return len(sql)


def _skip_comment(sql: str, index: int) -> int | None:
    """Position après un commentaire commençant en ``index``, sinon None."""
    if sql.startswith("--", index):
        end = sql.find("\n", index)
        return len(sql) if end < 0 else end
    if sql.startswith("/*", index):
        end = sql.find("*/", index + 2)
        return len(sql) if end < 0 else end + 2
    return None


def _literal_end(sql: str, index: int) -> int | None:
    """Fin d'une chaîne, d'un identifiant ou d'un bloc $tag$...$tag$ commençant en ``index``."""
    char = sql[index]
    if char in "'\"":
        return _quoted_end(sql, index, char)
    if char == "$":
        match = DOLLAR_TAG_RE.match(sql, index)
        if match:
            end = sql.find(match.group(0), match.end())
            return len(sql) if end < 0 else end + len(match.group(0))
    return None


def split_statements(sql: str) -> list[str]:
    """Découpe un script en instructions sur les ``;`` de premier niveau.

    Respecte les chaînes, identifiants entre guillemets, blocs dollar ($$, $fn$) et
    commentaires (retirés). Les chaînes E'...' à antislash ne sont pas gérées.
    """
    statements: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(sql):
        after_comment = _skip_comment(sql, index)
        if after_comment is not None:
            current.append(" ")
            index = after_comment
            continue
        literal_end = _literal_end(sql, index)
        if literal_end is not None:
            current.append(sql[index:literal_end])
            index = literal_end
            continue
        if sql[index] == ";":
            statements.append("".join(current).strip())
            current = []
        else:
            current.append(sql[index])
        index += 1
    statements.append("".join(current).strip())
    return [statement for statement in statements if statement]


def to_libpq_url(url: str) -> str:
    """``postgresql+psycopg://…`` (SQLAlchemy) → ``postgresql://…`` (libpq)."""
    scheme, separator, rest = url.partition("://")
    if not separator or scheme.split("+")[0] not in ("postgresql", "postgres"):
        raise MigrationError("L'URL de base de données doit désigner PostgreSQL.")
    return f"postgresql://{rest}"


# --- Orchestration -----------------------------------------------------------------------------

def apply_file(db: MigrationDatabase, item: MigrationFile) -> None:
    statements = split_statements(item.sql)
    for position, statement in enumerate(statements, start=1):
        try:
            db.execute(statement)
        except MigrationError as exc:
            raise MigrationError(f"{item.version} : instruction {position}/{len(statements)} en échec ({exc})") from exc
    db.record(item.version, item.sha256)
    logger.info("migration appliquée", extra={"version": item.version, "statements": len(statements)})


def _report_dry_run(current: MigrationPlan) -> int:
    for item in current.pending:
        logger.info("migration en attente", extra={"version": item.version, "sha256": item.sha256})
    logger.info("simulation terminée", extra={"pending": len(current.pending)})
    return EXIT_OK


def _check_plan(current: MigrationPlan) -> None:
    for version in current.unknown:
        logger.warning("version inscrite sans fichier", extra={"version": version})
    if current.changed:
        raise MigrationError("Migrations déjà appliquées mais modifiées depuis : " + ", ".join(current.changed)
                             + ". Écrivez une nouvelle migration au lieu de modifier l'ancienne.")


def run_migrations(db: MigrationDatabase, files: Sequence[MigrationFile], dry_run: bool = False) -> int:
    """Applique les migrations en attente ; en simulation, se contente de les lister (sans verrou)."""
    if dry_run:
        current = plan(files, db.applied())
        _check_plan(current)
        return _report_dry_run(current)
    db.lock()
    try:
        db.ensure_table()
        current = plan(files, db.applied())
        _check_plan(current)
        for item in current.pending:
            apply_file(db, item)
        logger.info("migrations à jour", extra={"applied": len(current.pending), "total": len(files)})
        return EXIT_OK
    finally:
        db.unlock()


# --- Adaptateur PostgreSQL (psycopg 3) ---------------------------------------------------------

class PsycopgDatabase:
    """Connexion autocommit unique : le verrou consultatif de session couvre toute l'exécution."""

    def __init__(self, connection: Any, error_type: type[Exception]) -> None:
        self._connection = connection
        self._error_type = error_type

    @classmethod
    def connect(cls, url: str) -> PsycopgDatabase:
        try:
            import psycopg
        except ImportError as exc:
            raise MigrationError("Paquet psycopg absent : installez psycopg[binary].") from exc
        try:
            connection = psycopg.connect(to_libpq_url(url), autocommit=True)
        except psycopg.Error as exc:
            raise MigrationError(f"Connexion impossible : {exc.__class__.__name__}") from exc
        return cls(connection, psycopg.Error)

    def _run(self, statement: str, params: tuple[Any, ...] | None = None) -> Any:
        try:
            return self._connection.execute(statement, params)
        except self._error_type as exc:
            raise MigrationError(str(exc).strip()) from exc

    def lock(self) -> None:
        self._run("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))

    def unlock(self) -> None:
        self._run("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))

    def ensure_table(self) -> None:
        self._run(SCHEMA_MIGRATIONS_DDL)

    def applied(self) -> dict[str, str]:
        exists = self._run("SELECT to_regclass('public.schema_migrations')").fetchone()[0]
        if exists is None:
            return {}
        return dict(self._run("SELECT version, sha256 FROM schema_migrations").fetchall())

    def execute(self, statement: str) -> None:
        # Sans paramètres : psycopg envoie le texte tel quel (les %I des DO $$ restent intacts).
        self._run(statement)

    def record(self, version: str, sha256: str) -> None:
        self._run("INSERT INTO schema_migrations (version, sha256) VALUES (%s, %s)", (version, sha256))

    def close(self) -> None:
        self._connection.close()


def database_url(environ: Mapping[str, str]) -> str:
    url = environ.get("MIGRATION_DATABASE_URL") or environ.get("DATABASE_URL")
    if not url:
        raise MigrationError("MIGRATION_DATABASE_URL ou DATABASE_URL doit être défini.")
    return url


def main(argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None) -> int:
    env = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description="Applique les migrations SQL SmartAgri92.")
    parser.add_argument("--dry-run", action="store_true", help="liste les migrations en attente sans rien appliquer")
    parser.add_argument("--dir", default=env.get("MIGRATIONS_DIR", DEFAULT_MIGRATIONS_DIR))
    args = parser.parse_args(argv)
    configure_logging()
    try:
        files = discover(Path(args.dir))
        url = to_libpq_url(database_url(env))
    except MigrationError as exc:
        logger.error("configuration invalide", extra={"error": str(exc)})
        return EXIT_USAGE
    try:
        db = PsycopgDatabase.connect(url)
        try:
            return run_migrations(db, files, dry_run=args.dry_run)
        finally:
            db.close()
    except MigrationError as exc:
        logger.error("échec des migrations", extra={"error": str(exc)})
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())

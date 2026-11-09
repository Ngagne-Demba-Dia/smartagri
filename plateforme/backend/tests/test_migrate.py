"""Exécuteur de migrations : fonctions pures et orchestration avec une fausse base (sans PostgreSQL)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.db import migrate
from app.db.migrate import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_USAGE,
    MigrationError,
    checksum,
    discover,
    migration_file,
    plan,
    run_migrations,
    split_statements,
    to_libpq_url,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


class FakeDatabase:
    """Journalise les appels ; `fail_on` fait échouer une instruction donnée."""

    def __init__(self, applied: dict[str, str] | None = None, fail_on: str | None = None) -> None:
        self.recorded = dict(applied or {})
        self.fail_on = fail_on
        self.log: list[str] = []
        self.statements: list[str] = []

    def lock(self) -> None:
        self.log.append("lock")

    def unlock(self) -> None:
        self.log.append("unlock")

    def ensure_table(self) -> None:
        self.log.append("ensure_table")

    def applied(self) -> dict[str, str]:
        return dict(self.recorded)

    def execute(self, statement: str) -> None:
        if statement == self.fail_on:
            raise MigrationError("erreur simulée")
        self.statements.append(statement)

    def record(self, version: str, sha256: str) -> None:
        self.log.append(f"record:{version}")
        self.recorded[version] = sha256


FILES = (migration_file("001_init.sql", "CREATE TABLE a (id int);\nCREATE TABLE b (id int);"),
         migration_file("002_more.sql", "CREATE INDEX i ON a (id);"))


# --- Fonctions pures ---------------------------------------------------------------------------

def test_checksum_ignores_line_endings() -> None:
    assert checksum("SELECT 1;\r\nSELECT 2;\r\n") == checksum("SELECT 1;\nSELECT 2;\n")
    assert checksum("SELECT 1;") != checksum("SELECT 2;")


def test_discover_sorts_lexically_and_uses_stem_as_version(tmp_path: Path) -> None:
    for name in ("010_late.sql", "002_b.sql", "001_a.sql", "notes.txt"):
        (tmp_path / name).write_text("SELECT 1;", encoding="utf-8")
    assert [item.version for item in discover(tmp_path)] == ["001_a", "002_b", "010_late"]


def test_discover_rejects_missing_or_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(MigrationError):
        discover(tmp_path / "absent")
    with pytest.raises(MigrationError):
        discover(tmp_path)


def test_plan_separates_pending_changed_and_unknown() -> None:
    applied = {"001_init": "autre-empreinte", "000_old": "x"}
    current = plan(FILES, applied)
    assert [item.version for item in current.pending] == ["002_more"]
    assert current.changed == ("001_init",) and current.unknown == ("000_old",)
    assert plan(FILES, {item.version: item.sha256 for item in FILES}).pending == ()


def test_split_respects_strings_dollar_blocks_and_comments() -> None:
    sql = """
    -- commentaire ; ignoré
    INSERT INTO t VALUES ('a;b', 'l''apostrophe; ok');
    /* bloc ; commentaire */
    CREATE FUNCTION f() RETURNS trigger AS $fn$ BEGIN PERFORM 1; RETURN NEW; END $fn$ LANGUAGE plpgsql;
    DO $$ BEGIN EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', 't'); END $$;
    SELECT "col;umn" FROM t;
    """
    statements = split_statements(sql)
    assert len(statements) == 4
    assert statements[0] == "INSERT INTO t VALUES ('a;b', 'l''apostrophe; ok')"
    assert "PERFORM 1; RETURN NEW;" in statements[1]
    assert "%I" in statements[2] and statements[3] == 'SELECT "col;umn" FROM t'
    assert all("commentaire" not in statement for statement in statements)


def test_split_real_migrations_yields_single_statements() -> None:
    for item in discover(MIGRATIONS_DIR):
        statements = split_statements(item.sql)
        assert statements and all(statement.strip() for statement in statements), item.version
        aggregates = [s for s in statements if "timescaledb.continuous" in s]
        assert all(s.startswith("CREATE MATERIALIZED VIEW") for s in aggregates), item.version


def test_to_libpq_url_strips_driver_and_rejects_other_databases() -> None:
    assert to_libpq_url("postgresql+psycopg://u:p@h:5432/db") == "postgresql://u:p@h:5432/db"
    assert to_libpq_url("postgres://u@h/db") == "postgresql://u@h/db"
    for url in ("sqlite://", "mysql://u@h/db", "pas-une-url"):
        with pytest.raises(MigrationError):
            to_libpq_url(url)


# --- Orchestration -----------------------------------------------------------------------------

def test_run_applies_pending_in_order_under_lock() -> None:
    db = FakeDatabase()
    assert run_migrations(db, FILES) == EXIT_OK
    assert db.log == ["lock", "ensure_table", "record:001_init", "record:002_more", "unlock"]
    assert db.statements == ["CREATE TABLE a (id int)", "CREATE TABLE b (id int)", "CREATE INDEX i ON a (id)"]
    db.log.clear()
    assert run_migrations(db, FILES) == EXIT_OK
    assert db.log == ["lock", "ensure_table", "unlock"]


def test_failed_statement_is_not_recorded_and_lock_is_released() -> None:
    db = FakeDatabase(fail_on="CREATE TABLE b (id int)")
    with pytest.raises(MigrationError, match="001_init : instruction 2/2"):
        run_migrations(db, FILES)
    assert "001_init" not in db.recorded and db.log[-1] == "unlock"


def test_changed_checksum_aborts_before_any_statement() -> None:
    db = FakeDatabase(applied={"001_init": "modifiee"})
    with pytest.raises(MigrationError, match="001_init"):
        run_migrations(db, FILES)
    assert db.statements == [] and db.log == ["lock", "ensure_table", "unlock"]


def test_dry_run_takes_no_lock_and_writes_nothing() -> None:
    db = FakeDatabase()
    assert run_migrations(db, FILES, dry_run=True) == EXIT_OK
    assert db.log == [] and db.statements == [] and db.recorded == {}


def test_main_reports_configuration_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(migrate, "configure_logging", lambda: None)
    (tmp_path / "001_a.sql").write_text("SELECT 1;", encoding="utf-8")
    assert migrate.main(["--dir", str(tmp_path)], environ={}) == EXIT_USAGE
    assert migrate.main(["--dir", str(tmp_path / "absent")], environ={"DATABASE_URL": "postgresql://h/db"}) \
        == EXIT_USAGE
    assert migrate.main(["--dir", str(tmp_path)], environ={"DATABASE_URL": "sqlite://"}) == EXIT_USAGE


def test_main_runs_with_injected_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = FakeDatabase()
    closed: list[bool] = []
    db.close = lambda: closed.append(True)  # type: ignore[attr-defined]
    urls: list[str] = []

    def fake_connect(url: str) -> FakeDatabase:
        urls.append(url)
        return db

    monkeypatch.setattr(migrate, "configure_logging", lambda: None)
    monkeypatch.setattr(migrate.PsycopgDatabase, "connect", staticmethod(fake_connect))
    (tmp_path / "001_a.sql").write_text("SELECT 1;", encoding="utf-8")
    env = {"MIGRATIONS_DIR": str(tmp_path), "DATABASE_URL": "postgresql+psycopg://app@h/db",
           "MIGRATION_DATABASE_URL": "postgresql://owner@h/db"}
    assert migrate.main([], environ=env) == EXIT_OK
    assert urls == ["postgresql://owner@h/db"] and db.recorded.keys() == {"001_a"} and closed == [True]
    db.fail_on = "SELECT 2"
    (tmp_path / "002_b.sql").write_text("SELECT 2;", encoding="utf-8")
    assert migrate.main([], environ=env) == EXIT_FAILED

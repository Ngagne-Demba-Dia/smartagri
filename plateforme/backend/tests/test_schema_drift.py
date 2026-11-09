"""Dérive ORM ↔ migrations SQL : les tests tournent sur SQLite (ORM), la production sur db/migrations.

Chaque table, colonne, nullabilité, contrainte CHECK/UNIQUE nommée et index nommé déclaré dans
l'ORM doit exister dans les scripts SQL. Les objets présents seulement en SQL (colonnes générées,
agrégats continus, politiques RLS) sont admis.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from sqlalchemy import Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.db.models  # noqa: F401  (enregistre toutes les tables dans les métadonnées)
from app.db.base import Base

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"
CREATE_TABLE = re.compile(r"CREATE TABLE IF NOT EXISTS (\w+) \(", re.IGNORECASE)
ALTER_TABLE = re.compile(r"ALTER TABLE (?:IF EXISTS )?(\w+)\s+(.*?);", re.IGNORECASE | re.DOTALL)
ADD_COLUMN = re.compile(r"ADD COLUMN (?:IF NOT EXISTS )?(\w+)\s+(.*)", re.IGNORECASE | re.DOTALL)
TABLE_KEYWORDS = ("constraint", "primary key", "unique", "check", "foreign key", "exclude")
DIALECT = postgresql.dialect()


@dataclass
class SqlTable:
    columns: dict[str, str] = field(default_factory=dict)
    primary_key: set[str] = field(default_factory=set)


def split_top_level(body: str) -> list[str]:
    """Découpe sur les virgules hors parenthèses et hors chaînes."""
    parts, depth, quoted, start = [], 0, False, 0
    for index, char in enumerate(body):
        if char == "'":
            quoted = not quoted
        elif not quoted and char in "()":
            depth += 1 if char == "(" else -1
        elif not quoted and depth == 0 and char == ",":
            parts.append(body[start:index].strip())
            start = index + 1
    parts.append(body[start:].strip())
    return [part for part in parts if part]


def closing_paren(text: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(text)):
        depth += {"(": 1, ")": -1}.get(text[index], 0)
        if depth == 0:
            return index
    raise ValueError("parenthèse non fermée")


def add_element(table: SqlTable, element: str) -> None:
    lowered = " ".join(element.lower().split())
    if lowered.startswith("primary key"):
        table.primary_key.update(name.strip() for name in lowered[lowered.index("(") + 1:-1].split(","))
    elif not lowered.startswith(TABLE_KEYWORDS):
        name, _, definition = lowered.partition(" ")
        table.columns[name] = definition


def parse_sql_tables(sql: str) -> dict[str, SqlTable]:
    tables: dict[str, SqlTable] = {}
    for match in CREATE_TABLE.finditer(sql):
        end = closing_paren(sql, match.end() - 1)
        table = tables.setdefault(match.group(1).lower(), SqlTable())
        for element in split_top_level(sql[match.end():end]):
            add_element(table, element)
    for match in ALTER_TABLE.finditer(sql):
        table = tables.setdefault(match.group(1).lower(), SqlTable())
        for clause in split_top_level(match.group(2)):
            added = ADD_COLUMN.match(clause)
            if added:
                add_element(table, f"{added.group(1)} {added.group(2)}")
    return tables


@pytest.fixture(scope="module")
def sql_text() -> str:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        pytest.skip(f"migrations introuvables : {MIGRATIONS_DIR}")
    raw = "\n".join(path.read_text(encoding="utf-8") for path in files)
    return re.sub(r"--[^\n]*", "", raw)


@pytest.fixture(scope="module")
def sql_tables(sql_text: str) -> dict[str, SqlTable]:
    return parse_sql_tables(sql_text)


def orm_tables() -> list[Table]:
    return sorted(Base.metadata.tables.values(), key=lambda table: table.name)


def column_problems(table: Table, sql: SqlTable) -> list[str]:
    problems = []
    for column in table.columns:
        definition = sql.columns.get(column.name)
        if definition is None:
            problems.append(f"{table.name}.{column.name} : colonne absente du SQL")
            continue
        sql_not_null = "not null" in definition or "primary key" in definition or column.name in sql.primary_key
        if not column.nullable and not sql_not_null:
            problems.append(f"{table.name}.{column.name} : NOT NULL dans l'ORM, nullable en SQL")
        if column.nullable and "not null" in definition and "default" not in definition:
            problems.append(f"{table.name}.{column.name} : NOT NULL sans DEFAULT en SQL, nullable dans l'ORM")
    return problems


# --- Analyseur ---------------------------------------------------------------------------------

def test_parser_reads_columns_constraints_and_alter_table() -> None:
    sql = ("CREATE TABLE IF NOT EXISTS t (\n id uuid PRIMARY KEY,\n price numeric(10, 2) NOT NULL,\n"
           " kind text CHECK (kind IN ('a', 'b,c')),\n CONSTRAINT ck_t_price CHECK (price > 0),\n"
           " PRIMARY KEY (id, price)\n);\nALTER TABLE t\n ADD COLUMN IF NOT EXISTS extra integer;")
    parsed = parse_sql_tables(sql)["t"]
    assert parsed.columns == {"id": "uuid primary key", "price": "numeric(10, 2) not null",
                              "kind": "text check (kind in ('a', 'b,c'))", "extra": "integer"}
    assert parsed.primary_key == {"id", "price"}


# --- Dérive ------------------------------------------------------------------------------------

def test_every_orm_table_and_column_exists_in_sql(sql_tables: dict[str, SqlTable]) -> None:
    problems = []
    for table in orm_tables():
        sql = sql_tables.get(table.name)
        if sql is None:
            problems.append(f"{table.name} : table absente du SQL")
            continue
        problems.extend(column_problems(table, sql))
    assert problems == []


def test_named_constraints_exist_in_sql(sql_text: str) -> None:
    expected = set()
    for table in orm_tables():
        ddl = str(CreateTable(table).compile(dialect=DIALECT))
        expected.update(re.findall(r"CONSTRAINT (\w+) (?:CHECK|UNIQUE)", ddl))
    missing = sorted(name for name in expected if not re.search(rf"CONSTRAINT {name}\b", sql_text))
    assert expected and missing == []


def test_named_indexes_exist_in_sql(sql_text: str) -> None:
    expected = set()
    for table in orm_tables():
        for index in table.indexes:
            expected.update(re.findall(r"INDEX (\w+) ON", str(CreateIndex(index).compile(dialect=DIALECT))))
    missing = sorted(name for name in expected if not re.search(rf"INDEX IF NOT EXISTS {name}\b", sql_text))
    assert expected and missing == []

"""Couche DB locale SQLite (reproduit /db/{collection} sur les 27 tables CSV de référence)."""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "data" / "smartagri_local.db"
_SAFE_IDENT = re.compile(r"[^a-zA-Z0-9_]")


def _clean_ident(name: str) -> str:
    cleaned = _SAFE_IDENT.sub("_", name).strip("_")
    return cleaned or "col"


class LocalMetricsDB:
    """Charge les 27 CSV (`metrics/`, `rag/`, `shap/`) dans SQLite pour requêtage rapide."""

    def __init__(self, root: Optional[Path] = None, db_path: Optional[Path] = None):
        self.root = Path(root) if root else ROOT
        self.db_path = Path(db_path) if db_path else (self.root / "data" / "smartagri_local.db")
        self.collections: Dict[str, Dict[str, Any]] = {}
        self._sync()

    def _csv_sources(self) -> List[Path]:
        files: List[Path] = []
        for folder in (
            self.root / "metrics",
            self.root / "rag" / "chunks",
            self.root / "rag" / "evaluation",
            self.root / "shap",
        ):
            if folder.exists():
                files.extend(sorted(folder.glob("*.csv")))
        return files

    def _sync(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn_target: Any = self.db_path
            with sqlite3.connect(conn_target) as _:
                pass
        except OSError:
            conn_target = ":memory:"
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
        sources = self._csv_sources()
        conn = getattr(self, "_mem_conn", None) or sqlite3.connect(self.db_path)
        try:
            for csv_path in sources:
                table = _clean_ident(csv_path.stem)
                with csv_path.open("r", encoding="utf-8", newline="") as fh:
                    reader = csv.reader(fh)
                    header = next(reader, None)
                    if not header:
                        continue
                    cols = [_clean_ident(c) for c in header]
                    # Dédupliquer d'éventuels noms identiques après nettoyage
                    seen: Dict[str, int] = {}
                    uniq_cols: List[str] = []
                    for c in cols:
                        cnt = seen.get(c, 0)
                        seen[c] = cnt + 1
                        uniq_cols.append(c if cnt == 0 else f"{c}_{cnt}")
                    rows = [r[: len(uniq_cols)] + [""] * max(0, len(uniq_cols) - len(r)) for r in reader]

                col_defs = ", ".join(f'"{c}" TEXT' for c in uniq_cols)
                conn.execute(f'DROP TABLE IF EXISTS "{table}"')
                conn.execute(f'CREATE TABLE "{table}" ({col_defs})')
                if rows:
                    placeholders = ", ".join("?" for _ in uniq_cols)
                    conn.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)
                self.collections[table] = {
                    "collection": table,
                    "source": str(csv_path.relative_to(self.root)).replace("\\", "/"),
                    "rows": len(rows),
                    "columns": uniq_cols,
                }
            conn.commit()
        finally:
            if not hasattr(self, "_mem_conn"):
                conn.close()

    def list_collections(self) -> List[Dict[str, Any]]:
        return [self.collections[k] for k in sorted(self.collections)]

    def query(self, collection: str, limit: int = 50, offset: int = 0) -> Optional[Dict[str, Any]]:
        key = _clean_ident(collection)
        meta = self.collections.get(key)
        if meta is None:
            return None
        limit = max(1, min(limit, 500))
        offset = max(0, offset)
        conn = getattr(self, "_mem_conn", None) or sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(f'SELECT * FROM "{key}" LIMIT ? OFFSET ?', (limit, offset))
            items = [dict(r) for r in cur.fetchall()]
        finally:
            if not hasattr(self, "_mem_conn"):
                conn.close()
        return {
            "collection": key,
            "total_rows": meta["rows"],
            "limit": limit,
            "offset": offset,
            "items": items,
        }

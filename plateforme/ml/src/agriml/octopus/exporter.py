"""Exporteur d'instantanés pour OctOpus : minimisation, pseudonymisation, manifeste. Rien ne sort sans filtrage.

Règles appliquées (première barrière ; les garde-fous OctOpus ne sont que la seconde) :
- colonnes `drop` supprimées (nom, téléphone, e-mail, commentaires libres…) ;
- colonnes `mask` vidées (schéma conservé, valeurs retirées) ;
- colonnes `pseudonymize` remplacées par HMAC-SHA256(sel, valeur) tronqué : clés stables pour un même sel,
  impossibles à relier aux identifiants sans le sel ;
- colonnes `round_coords` arrondies à 0,01° (≈ 1,1 km) sous le nom `<col>_r`, l'original est supprimé ;
- REFUS d'écrire quoi que ce soit si une colonne interdite subsiste (nom de colonne ou valeurs ressemblant à
  un téléphone / e-mail, coordonnées non arrondies).

Le sel vient de AGRIML_PSEUDO_SALT (Secrets Manager) et n'est JAMAIS écrit ni journalisé : le manifeste ne
garde que son identifiant (AGRIML_PSEUDO_SALT_ID, sinon une empreinte HMAC non réversible).
Sortie : `<out>/octopus/<jeu>/v=<version>/` (même arborescence que `s3://agri-curated-<env>/octopus/`),
instantané immuable : une version déjà publiée n'est jamais réécrite.

Usage :
    python -m agriml.octopus.exporter --program irrigation_need --train data.parquet --version 20261126-3f2a9c1
                                      --out data/curated --source-query irrigation_need_v1.sql
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import logging
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from agriml import __version__
from agriml.io import git_sha, sha256_file, write_json, write_table

logger = logging.getLogger(__name__)

SALT_ENV = "AGRIML_PSEUDO_SALT"
SALT_ID_ENV = "AGRIML_PSEUDO_SALT_ID"
MIN_SALT_CHARS = 32
PSEUDO_HEX_CHARS = 16  # 64 bits : collisions négligeables jusqu'à des millions d'identifiants
COORD_DECIMALS = 2
ROUNDED_SUFFIX = "_r"
MASK_VALUE = pd.NA
S3_ROOT = "octopus"
MANIFEST = "manifest.json"
FORBIDDEN_TOKENS = frozenset({
    "name", "nom", "prenom", "firstname", "lastname", "owner", "phone", "telephone", "tel", "mobile", "msisdn",
    "whatsapp", "email", "mail", "address", "adresse", "cni", "nin", "passport", "iban", "comment",
    "commentaire", "notes", "message", "chat", "photo_exif",
})
COORD_TOKENS = frozenset({"lat", "lon", "lng", "latitude", "longitude", "gps", "geom", "geometry"})
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+|00)\d[\d .-]{7,15}\d|\b7[05678]\d{7}\b|\b7[05678][ .]?\d{3}[ .]?\d{2}[ .]?\d{2}\b")
_SAFE_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ExportRefused(ValueError):
    """Instantané refusé : donnée interdite, sel absent ou version déjà publiée. Rien n'a été écrit."""


@dataclass(frozen=True)
class PrivacyPolicy:
    drop: tuple[str, ...] = ()
    mask: tuple[str, ...] = ()
    pseudonymize: tuple[str, ...] = ()
    round_coords: tuple[str, ...] = ()
    allow: tuple[str, ...] = ()  # exceptions explicites et revues (ex. « variety_name » = nom de variété)
    coord_decimals: int = COORD_DECIMALS

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any] | None) -> PrivacyPolicy:
        mapping = dict(mapping or {})
        unknown = set(mapping) - {f for f in cls.__dataclass_fields__}
        if unknown:
            raise ValueError(f"Garde-fous inconnus : {sorted(unknown)}")
        return cls(**{k: (tuple(v) if isinstance(v, list | tuple) else v) for k, v in mapping.items()})

    def to_dict(self) -> dict[str, Any]:
        return {"drop": list(self.drop), "mask": list(self.mask), "pseudonymize": list(self.pseudonymize),
                "round_coords": list(self.round_coords), "coord_decimals": self.coord_decimals}


@dataclass(frozen=True)
class ExportResult:
    folder: Path
    manifest: dict[str, Any] = field(repr=False)
    manifest_sha256: str = ""


# --------------------------------------------------------------------------- sel et pseudonymisation


def load_salt(env: Mapping[str, str] | None = None) -> tuple[bytes, str]:
    """(sel, identifiant du sel). Le sel n'est jamais renvoyé ailleurs qu'à l'appelant."""
    env = os.environ if env is None else env
    salt = env.get(SALT_ENV, "")
    if len(salt) < MIN_SALT_CHARS:
        raise ExportRefused(f"Sel de pseudonymisation absent ou trop court : définir {SALT_ENV} "
                            f"(≥ {MIN_SALT_CHARS} caractères, depuis Secrets Manager).")
    key = salt.encode("utf-8")
    salt_id = env.get(SALT_ID_ENV) or "hmac-" + hmac.new(key, b"agriml-salt-id", hashlib.sha256).hexdigest()[:12]
    return key, salt_id


def pseudonymize_series(values: pd.Series, salt: bytes) -> pd.Series:
    """HMAC-SHA256(sel, str(valeur)) tronqué ; les valeurs manquantes restent manquantes."""
    def _one(v: Any) -> Any:
        if pd.isna(v):
            return pd.NA
        return hmac.new(salt, str(v).encode("utf-8"), hashlib.sha256).hexdigest()[:PSEUDO_HEX_CHARS]
    return values.map(_one).astype("string")


def apply_policy(df: pd.DataFrame, policy: PrivacyPolicy, salt: bytes) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Nouvelle table filtrée + résumé des transformations (l'entrée n'est jamais modifiée)."""
    present = set(df.columns)
    dropped = [c for c in policy.drop if c in present]
    out = df.drop(columns=dropped)
    updates = {c: pd.Series(MASK_VALUE, index=out.index, dtype="string") for c in policy.mask if c in present}
    updates |= {c: pseudonymize_series(out[c], salt) for c in policy.pseudonymize if c in present}
    out = out.assign(**updates)
    rounded = {}
    for col in (c for c in policy.round_coords if c in present):
        new = f"{col}{ROUNDED_SUFFIX}"
        out = out.assign(**{new: pd.to_numeric(out[col], errors="coerce").round(policy.coord_decimals)})
        out = out.drop(columns=[col])
        rounded[new] = 10.0 ** -policy.coord_decimals
    missing = sorted(set(policy.drop + policy.mask + policy.pseudonymize + policy.round_coords) - present)
    if missing:
        logger.info("Garde-fous sans effet (colonnes absentes) : %s", missing)
    info = {"dropped_columns": dropped, "masked_columns": sorted(updates.keys() & set(policy.mask)),
            "pseudonymized_columns": [c for c in policy.pseudonymize if c in present], "rounded_columns": rounded}
    return out, info


# --------------------------------------------------------------------------- contrôle


def column_tokens(name: str) -> set[str]:
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name)).lower()
    tokens = {t for t in re.split(r"[^a-z0-9]+", snake) if t}
    return tokens | ({snake.replace("-", "_")} if "photo_exif" in snake else set())


def _value_violations(col: str, series: pd.Series) -> list[str]:
    if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
        return []
    text = series.dropna().astype(str)
    found = []
    for label, pattern in (("e-mail", EMAIL_RE), ("téléphone", PHONE_RE)):
        hits = int(text.str.contains(pattern).sum())
        if hits:
            found.append(f"{col} : {hits} valeur(s) ressemblant à un {label}")
    return found


def _coord_violation(col: str, series: pd.Series, decimals: int) -> str | None:
    if not col.endswith(ROUNDED_SUFFIX):
        return f"{col} : coordonnées non arrondies (ajouter à round_coords ou drop)"
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if values.size and not np.allclose(values, np.round(values, decimals), atol=1e-9):
        return f"{col} : précision supérieure à {decimals} décimales"
    return None


def find_violations(df: pd.DataFrame, policy: PrivacyPolicy) -> list[str]:
    """Liste des raisons de refus (vide = exportable)."""
    exempt_names = set(policy.pseudonymize) | set(policy.mask) | set(policy.allow)
    exempt_values = exempt_names | {c for c in df.columns if c.endswith(ROUNDED_SUFFIX)}
    problems = []
    for col in df.columns:
        tokens = column_tokens(col)
        if col not in exempt_names and tokens & FORBIDDEN_TOKENS:
            problems.append(f"{col} : colonne interdite ({', '.join(sorted(tokens & FORBIDDEN_TOKENS))})")
        if col not in set(policy.allow) and tokens & COORD_TOKENS:
            issue = _coord_violation(col, df[col], policy.coord_decimals)
            if issue:
                problems.append(issue)
        if col not in exempt_values:
            problems.extend(_value_violations(col, df[col]))
    return problems


# --------------------------------------------------------------------------- écriture


def check_part(value: str, what: str) -> str:
    if not _SAFE_PART.match(str(value)):
        raise ExportRefused(f"{what} invalide : {value!r}")
    return str(value)


def snapshot_key(dataset: str, version: str) -> str:
    """Préfixe S3 relatif au seau `agri-curated-<env>` : octopus/<jeu>/v=<version>/."""
    return f"{S3_ROOT}/{check_part(dataset, 'Jeu')}/v={check_part(version, 'Version')}/"


def _dtype_name(series: pd.Series) -> str:
    kinds = {"f": "float", "i": "int", "u": "int", "b": "bool", "M": "timestamp", "m": "duration"}
    return kinds.get(series.dtype.kind, "string")


def _readme(dataset: str, version: str, manifest: Mapping[str, Any]) -> str:
    cols = "\n".join(f"| {c} | {t} |" for c, t in manifest["schema"].items())
    return (f"# Jeu `{dataset}` — v={version}\n\nConfidentiel - réservé aux partenaires de travail.\n\n"
            f"- Cible : `{manifest.get('target')}` ; groupes : `{manifest.get('groups')}` ; "
            f"temps : `{manifest.get('time_column')}`\n- Lignes (entraînement) : {manifest['rows']}\n"
            f"- Pseudonymisation : HMAC-SHA256, sel `{manifest['pseudonymisation']['salt_id']}`\n"
            f"- Colonnes supprimées : {', '.join(manifest['dropped_columns']) or 'aucune'}\n"
            f"- Holdout envoyé : non\n\n| Colonne | Type |\n|---|---|\n{cols}\n")


def _write_tables(folder: Path, tables: Mapping[str, pd.DataFrame], file_format: str) -> dict[str, Path]:
    written = {}
    for stem, table in tables.items():
        path = folder / f"{stem}.{file_format}"
        if file_format == "csv":
            path.parent.mkdir(parents=True, exist_ok=True)
            table.to_csv(path, index=False, lineterminator="\n")
        else:
            path = write_table(table, path)
        written[path.name] = path
    return written


@dataclass(frozen=True)
class SnapshotSpec:
    """Description du jeu (cible, groupes, provenance) ; les garde-fous viennent du programme OctOpus."""

    dataset: str
    version: str
    policy: PrivacyPolicy
    source: Mapping[str, Any]
    target: str | None = None
    groups: str | None = None
    time_column: str | None = None
    holdout_window: Sequence[str] | None = None
    file_format: str = "parquet"


def _sanitize_all(tables: Mapping[str, pd.DataFrame], spec: SnapshotSpec, salt: bytes):
    clean, infos = {}, {}
    problems = []
    for stem, table in tables.items():
        clean[stem], infos[stem] = apply_policy(table, spec.policy, salt)
        problems += [f"[{stem}] {p}" for p in find_violations(clean[stem], spec.policy)]
    if problems:
        raise ExportRefused("Export refusé, données interdites :\n- " + "\n- ".join(problems))
    return clean, infos["train"]  # le manifeste décrit la politique appliquée au jeu d'entraînement


def build_snapshot_manifest(spec: SnapshotSpec, clean: Mapping[str, pd.DataFrame], info: Mapping[str, Any],
                            salt_id: str, files: Mapping[str, Path]) -> dict[str, Any]:
    train = clean["train"]
    return {
        "dataset": spec.dataset, "version": spec.version, "s3_prefix": snapshot_key(spec.dataset, spec.version),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"), "git_sha": git_sha(Path(__file__).parent),
        "agriml_version": __version__, "source": dict(spec.source), "rows": len(train),
        "test_rows": len(clean["test"]) if "test" in clean else None,
        "schema": {c: _dtype_name(train[c]) for c in train.columns}, "target": spec.target, "groups": spec.groups,
        "time_column": spec.time_column, "pseudonymisation": {"method": "HMAC-SHA256", "salt_id": salt_id},
        **info, "files": {name: f"sha256:{sha256_file(p)}" for name, p in sorted(files.items())},
        "holdout_window": list(spec.holdout_window) if spec.holdout_window else None, "holdout_sent": False,
    }


def export_snapshot(train: pd.DataFrame, out_root: str | Path, spec: SnapshotSpec, test: pd.DataFrame | None = None,
                    env: Mapping[str, str] | None = None) -> ExportResult:
    """Filtre, contrôle puis écrit l'instantané ; lève ExportRefused AVANT toute écriture en cas de problème."""
    folder = Path(out_root) / snapshot_key(spec.dataset, spec.version)
    if (folder / MANIFEST).exists():
        raise ExportRefused(f"Version déjà publiée (instantané immuable) : {folder}")
    if spec.target and spec.target not in train.columns:
        raise ExportRefused(f"Cible « {spec.target} » absente du jeu d'entraînement.")
    salt, salt_id = load_salt(env)
    tables = {"train": train} if test is None else {"train": train, "test": test}
    clean, info = _sanitize_all(tables, spec, salt)
    files = _write_tables(folder, clean, spec.file_format)
    readme = folder / "README.md"
    draft = build_snapshot_manifest(spec, clean, info, salt_id, files)
    readme.write_text(_readme(spec.dataset, spec.version, draft), encoding="utf-8")
    manifest = build_snapshot_manifest(spec, clean, info, salt_id, {**files, "README.md": readme})
    write_json(manifest, folder / MANIFEST)
    logger.info("Instantané %s écrit (%d lignes, %d colonnes) : %s", spec.dataset, len(clean["train"]),
                clean["train"].shape[1], folder)
    return ExportResult(folder, manifest, sha256_file(folder / MANIFEST))


def main(argv: Sequence[str] | None = None) -> int:
    from agriml.io import read_table
    from agriml.logs import setup_logging
    from agriml.octopus.programs import load_program

    parser = argparse.ArgumentParser(description="Exporte un instantané pseudonymisé pour OctOpus.")
    parser.add_argument("--program", required=True, help="Nom d'un programme (programs/<nom>.yaml) ou chemin.")
    parser.add_argument("--train", required=True)
    parser.add_argument("--test")
    parser.add_argument("--version", required=True, help="Ex. 20261126-3f2a9c1")
    parser.add_argument("--out", required=True, help="Racine locale (miroir du seau curated).")
    parser.add_argument("--source-query", required=True, help="Identifiant de la requête source.")
    parser.add_argument("--format", choices=("parquet", "csv"), default="parquet")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    program = load_program(args.program)
    spec = SnapshotSpec(program.dataset, args.version, program.guardrails, {"query_id": args.source_query},
                        program.target, program.groups, program.time_column, file_format=args.format)
    test = read_table(args.test) if args.test else None
    try:
        result = export_snapshot(read_table(args.train), args.out, spec, test)
    except ExportRefused as exc:
        logger.error("%s", exc)
        return 2
    logger.info("manifest.json sha256 = %s", result.manifest_sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

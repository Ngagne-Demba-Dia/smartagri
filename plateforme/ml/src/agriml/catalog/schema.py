"""Schéma du catalogue data/IA : sources → jeux de données → modèles (fichiers `ml/catalog/*.yaml`).

Le chargement contrôle la forme (champs connus, obligatoires, valeurs d'énumération) et regroupe tous les
problèmes dans une seule `CatalogError`. Les règles de cohérence entre fichiers sont dans `rules.py`.
Les objets sont figés : le catalogue chargé ne se modifie pas, il se recharge.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

CATALOG_DIR = Path(__file__).resolve().parents[3] / "catalog"
ENV_DIR = "AGRIML_CATALOG_DIR"

DOMAINS = ("meteo", "sols", "satellite", "drone", "iot", "phyto", "agronomie", "economie", "geo", "eau",
           "historique", "utilisateurs", "langue", "connaissances")
SOURCE_KINDS = ("public_api", "open_data", "commercial", "partner", "internal", "user_input", "reference",
                "pretrained")
COMMERCIAL = ("open", "contract", "restricted", "unknown")
PERSONAL = ("none", "indirect", "direct")             # ordonné : du moins au plus personnel
COVERAGE = ("full", "partial", "none", "unknown")
ZONES = ("raw", "curated", "features")
CLASSIFICATIONS = ("publique", "interne", "confidentielle", "personnelle")  # ordonné
POLICIES = ("forbidden", "public", "pseudonymised")
VERSIONS = ("MVP", "V1.1", "V2", "V3")                # ordonné
USE_CASES = tuple(f"IA-{i}" for i in range(1, 11)) + ("TRANSVERSE",)
MODEL_KINDS = ("rules", "physical", "statistics", "ml", "deep_learning", "llm", "optimisation")
LEVELS = ("mandatory", "recommended", "optional")     # ordonné : du plus au moins nécessaire
INFERENCE_MODES = ("batch", "online", "edge", "stream")
VARIANTS = ("competition", "production", "compromis")
WEB_MODULES = range(1, 14)
PLATFORM_RE = re.compile(r"^(web:(\d+)|mobile|kit|partner)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CatalogError(ValueError):
    """Catalogue illisible ou mal formé ; `problems` liste tous les défauts, pas seulement le premier."""

    def __init__(self, problems: list[str]):
        self.problems = tuple(problems)
        super().__init__("Catalogue invalide :\n  - " + "\n  - ".join(problems))


@dataclass(frozen=True)
class Source:
    id: str
    domain: str
    kind: str
    name: str
    licence: str
    commercial: str
    personal: str
    coverage: str
    cost: str = ""
    access: str = ""
    details: str = ""
    verified: str | None = None
    evidence: str | None = None
    identifying: bool = False


@dataclass(frozen=True)
class OctopusPolicy:
    policy: str = "forbidden"
    name: str | None = None
    licence_cleared: bool = False


@dataclass(frozen=True)
class Dataset:
    id: str
    zone: str
    domain: str
    available: str
    classification: str
    inputs: tuple[str, ...]
    content: str
    grain: str = ""
    refresh: str = ""
    volume: str = ""
    retention: str = ""
    minimised: bool = False
    aggregated: bool = False
    research_only: bool = False
    holdout: bool = False
    octopus: OctopusPolicy = OctopusPolicy()


@dataclass(frozen=True)
class Inference:
    mode: str
    fallback: str
    latency: str = ""
    frequency: str = ""


@dataclass(frozen=True)
class Metrics:
    primary: str
    threshold: str
    secondary: tuple[str, ...] = ()


@dataclass(frozen=True)
class Model:
    id: str
    use_case: str
    name: str
    kind: str
    version: str
    platform: tuple[str, ...]
    data: Mapping[str, tuple[str, ...]]
    candidates: Mapping[str, str]
    metrics: Metrics
    training: str
    inference: Inference
    features: tuple[str, ...] = ()
    pretrained: tuple[str, ...] = ()
    pretrained_research: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    octopus_program: str | None = None
    challenge: str | None = None

    def datasets(self, *levels: str) -> tuple[str, ...]:
        """Jeux lus aux niveaux demandés (tous si aucun), dans l'ordre mandatory → optional."""
        return tuple(d for level in (levels or LEVELS) for d in self.data.get(level, ()))


@dataclass(frozen=True)
class Catalog:
    """Les trois listes dans l'ordre des fichiers (doublons compris : règle 9) et leurs index par id."""

    directory: Path
    sources: tuple[Source, ...]
    datasets: tuple[Dataset, ...]
    models: tuple[Model, ...]

    @property
    def source_by_id(self) -> Mapping[str, Source]:
        return MappingProxyType({s.id: s for s in self.sources})

    @property
    def dataset_by_id(self) -> Mapping[str, Dataset]:
        return MappingProxyType({d.id: d for d in self.datasets})

    @property
    def model_by_id(self) -> Mapping[str, Model]:
        return MappingProxyType({m.id: m for m in self.models})


# ---------------------------------------------------------------------------------------------- analyse
class _Reader:
    """Lit une entrée YAML en notant les défauts au lieu de s'arrêter au premier."""

    def __init__(self, problems: list[str], where: str, raw: Any, allowed: set[str]):
        self.problems, self.where = problems, where
        self.raw: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
        if not isinstance(raw, Mapping):
            self.fail("entrée attendue sous forme de dictionnaire")
        for key in sorted(set(self.raw) - allowed):
            self.fail(f"champ inconnu « {key} »")

    def fail(self, message: str) -> None:
        self.problems.append(f"{self.where} : {message}")

    def text(self, key: str, required: bool = True, default: str = "") -> str:
        value = self.raw.get(key)
        if value is None:
            if required:
                self.fail(f"champ obligatoire « {key} » absent")
            return default
        if not isinstance(value, str) or (required and not value.strip()):
            self.fail(f"« {key} » doit être un texte non vide")
            return default
        return value

    def optional_text(self, key: str) -> str | None:
        value = self.raw.get(key)
        if value is not None and not isinstance(value, str):
            self.fail(f"« {key} » doit être un texte ou null")
            return None
        return value

    def choice(self, key: str, options: tuple[str, ...], default: str | None = None) -> str:
        value = self.raw.get(key, default)
        if value not in options:
            self.fail(f"« {key} » = {value!r} hors de {{{', '.join(options)}}}")
            return options[0]
        return value

    def flag(self, key: str) -> bool:
        value = self.raw.get(key, False)
        if not isinstance(value, bool):
            self.fail(f"« {key} » doit valoir true ou false")
            return False
        return value

    def ids(self, key: str, required: bool = False) -> tuple[str, ...]:
        value = self.raw.get(key)
        if value is None:
            if required:
                self.fail(f"champ obligatoire « {key} » absent")
            return ()
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            self.fail(f"« {key} » doit être une liste de textes")
            return ()
        return tuple(value)

    def mapping(self, key: str) -> Mapping[str, Any]:
        value = self.raw.get(key)
        if not isinstance(value, Mapping):
            self.fail(f"« {key} » doit être un dictionnaire")
            return {}
        return value


def _parse_source(problems: list[str], raw: Any, index: int) -> Source:
    r = _Reader(problems, f"sources[{index}] {_id_of(raw)}", raw,
                {"id", "domain", "kind", "name", "licence", "commercial", "personal", "coverage", "cost",
                 "access", "details", "verified", "evidence", "identifying"})
    verified = r.optional_text("verified")
    if verified is not None and not DATE_RE.match(verified):
        r.fail(f"« verified » = {verified!r} : date AAAA-MM-JJ entre guillemets attendue")
    return Source(id=r.text("id"), domain=r.choice("domain", DOMAINS), kind=r.choice("kind", SOURCE_KINDS),
                  name=r.text("name"), licence=r.text("licence"),
                  commercial=r.choice("commercial", COMMERCIAL),
                  personal=r.choice("personal", PERSONAL), coverage=r.choice("coverage", COVERAGE),
                  cost=r.text("cost", required=False), access=r.text("access", required=False),
                  details=r.text("details", required=False), verified=verified,
                  evidence=r.optional_text("evidence"), identifying=r.flag("identifying"))


def _parse_octopus(r: _Reader) -> OctopusPolicy:
    if "octopus" not in r.raw:
        return OctopusPolicy()
    sub = _Reader(r.problems, f"{r.where} octopus", r.raw["octopus"], {"policy", "name", "licence_cleared"})
    return OctopusPolicy(policy=sub.choice("policy", POLICIES, "forbidden"), name=sub.optional_text("name"),
                         licence_cleared=sub.flag("licence_cleared"))


def _parse_dataset(problems: list[str], raw: Any, index: int) -> Dataset:
    r = _Reader(problems, f"datasets[{index}] {_id_of(raw)}", raw,
                {"id", "zone", "domain", "available", "classification", "inputs", "content", "grain",
                 "refresh", "volume", "retention", "minimised", "aggregated", "research_only", "holdout",
                 "octopus"})
    inputs = r.ids("inputs", required=True)
    if not inputs and "inputs" in r.raw:
        r.fail("« inputs » ne peut pas être vide")
    return Dataset(id=r.text("id"), zone=r.choice("zone", ZONES), domain=r.choice("domain", DOMAINS),
                   available=r.choice("available", VERSIONS),
                   classification=r.choice("classification", CLASSIFICATIONS), inputs=inputs,
                   content=r.text("content"), grain=r.text("grain", required=False),
                   refresh=r.text("refresh", required=False), volume=r.text("volume", required=False),
                   retention=r.text("retention", required=False), minimised=r.flag("minimised"),
                   aggregated=r.flag("aggregated"), research_only=r.flag("research_only"),
                   holdout=r.flag("holdout"), octopus=_parse_octopus(r))


def _parse_platforms(r: _Reader) -> tuple[str, ...]:
    platforms = r.ids("platform", required=True)
    for p in platforms:
        match = PLATFORM_RE.match(p)
        if not match or (match.group(2) and int(match.group(2)) not in WEB_MODULES):
            r.fail(f"plateforme {p!r} invalide (web:1 … web:13, mobile, kit, partner)")
    return platforms


def _parse_model_parts(r: _Reader) -> tuple[dict[str, tuple[str, ...]], dict[str, str], Metrics, Inference]:
    data_r = _Reader(r.problems, f"{r.where} data", r.mapping("data"), set(LEVELS))
    data = {level: data_r.ids(level) for level in LEVELS}
    if not data["mandatory"]:
        r.fail("au moins un jeu obligatoire (data.mandatory) est requis")
    cand_r = _Reader(r.problems, f"{r.where} candidates", r.mapping("candidates"), set(VARIANTS))
    candidates = {v: cand_r.text(v) for v in VARIANTS}
    met_r = _Reader(r.problems, f"{r.where} metrics", r.mapping("metrics"),
                    {"primary", "secondary", "threshold"})
    metrics = Metrics(primary=met_r.text("primary"), threshold=met_r.text("threshold"),
                      secondary=met_r.ids("secondary"))
    inf_r = _Reader(r.problems, f"{r.where} inference", r.mapping("inference"),
                    {"mode", "latency", "frequency", "fallback"})
    inference = Inference(mode=inf_r.choice("mode", INFERENCE_MODES), fallback=inf_r.text("fallback"),
                          latency=inf_r.text("latency", required=False),
                          frequency=inf_r.text("frequency", required=False))
    return data, candidates, metrics, inference


def _parse_model(problems: list[str], raw: Any, index: int) -> Model:
    r = _Reader(problems, f"models[{index}] {_id_of(raw)}", raw,
                {"id", "use_case", "name", "kind", "version", "platform", "data", "features", "candidates",
                 "metrics", "training", "inference", "pretrained", "pretrained_research", "depends_on",
                 "octopus_program", "challenge"})
    data, candidates, metrics, inference = _parse_model_parts(r)
    return Model(id=r.text("id"), use_case=r.choice("use_case", USE_CASES), name=r.text("name"),
                 kind=r.choice("kind", MODEL_KINDS), version=r.choice("version", VERSIONS),
                 platform=_parse_platforms(r), data=MappingProxyType(data),
                 candidates=MappingProxyType(candidates), metrics=metrics, training=r.text("training"),
                 inference=inference, features=r.ids("features"), pretrained=r.ids("pretrained"),
                 pretrained_research=r.ids("pretrained_research"), depends_on=r.ids("depends_on"),
                 octopus_program=r.optional_text("octopus_program"), challenge=r.optional_text("challenge"))


def _id_of(raw: Any) -> str:
    return str(raw.get("id", "?")) if isinstance(raw, Mapping) else "?"


def _read_list(problems: list[str], path: Path, key: str) -> list[Any]:
    if not path.exists():
        problems.append(f"{path.name} : fichier absent de {path.parent}")
        return []
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        problems.append(f"{path.name} : YAML illisible ({exc})")
        return []
    entries = content.get(key) if isinstance(content, Mapping) else None
    if not isinstance(entries, list):
        problems.append(f"{path.name} : clé racine « {key} » (liste) attendue")
        return []
    return entries


def resolve_dir(directory: str | Path | None = None) -> Path:
    """Dossier explicite, sinon variable AGRIML_CATALOG_DIR, sinon `ml/catalog`."""
    return Path(directory or os.environ.get(ENV_DIR) or CATALOG_DIR)


def load_catalog(directory: str | Path | None = None) -> Catalog:
    """Charge les trois fichiers ; lève `CatalogError` avec la liste complète des défauts de forme."""
    base = resolve_dir(directory)
    problems: list[str] = []
    parts: dict[str, tuple[Any, ...]] = {}
    parsers: dict[str, Callable[[list[str], Any, int], Any]] = {
        "sources": _parse_source, "datasets": _parse_dataset, "models": _parse_model}
    for key, parser in parsers.items():
        entries = _read_list(problems, base / f"{key}.yaml", key)
        parts[key] = tuple(parser(problems, raw, i) for i, raw in enumerate(entries))
    if problems:
        raise CatalogError(problems)
    return Catalog(directory=base, sources=parts["sources"], datasets=parts["datasets"],
                   models=parts["models"])

"""Règles de cohérence du catalogue (voir ml/catalog/README.md, § Règles).

1. références par zone (raw ← sources, curated ← raw|curated, features ← curated|features,
   modèle ← curated|features),
   modèles pré-entraînés et dépendances entre modèles ;
2. graphe des jeux sans cycle ;
3. donnée personnelle calculée depuis l'amont, et classification minimale qui en découle ;
4. politique OctOpus (raw interdit, public sans donnée personnelle, pseudonymised = features + holdout) ;
5. licences (non commercial ⇒ research_only, jamais obligatoire ni recommandé ; contract/unknown signalés) ;
6. disponibilité des jeux et des modèles cohérente avec les versions ;
7. synchronisation avec les programmes OctOpus (`agriml/octopus/programs/*.yaml`) ;
8. sources et jeux inutilisés ;
9. identifiants uniques.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from types import MappingProxyType

from agriml.catalog.schema import (
    CLASSIFICATIONS,
    LEVELS,
    PERSONAL,
    VERSIONS,
    Catalog,
    Dataset,
    Model,
)

ERROR, WARNING = "error", "warning"
SANDBOX_WORKSPACES = ("agri92-sandbox",)
PRIVATE_WORKSPACES = ("agri92-pilot", "agri92-prod")
COMPETITION_PREFIX = "competition"
ALLOWED_INPUT_ZONES = {"curated": ("raw", "curated"), "features": ("curated", "features")}
MODEL_INPUT_ZONES = ("curated", "features")


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    subject: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.code} · {self.subject} : {self.message}"


@dataclass(frozen=True)
class ProgramRef:
    """Ce que le catalogue doit savoir d'un programme OctOpus : son jeu et son espace de travail."""

    name: str
    dataset: str
    workspace: str


@dataclass(frozen=True)
class Lineage:
    """Amont d'un modèle : niveau le plus fort par jeu et par source (mandatory > recommended > optional)."""

    model: str
    datasets: Mapping[str, str]
    sources: Mapping[str, str]


def load_program_refs() -> tuple[ProgramRef, ...]:
    """Programmes versionnés du dépôt (import paresseux : le catalogue reste lisible sans les extras)."""
    from agriml.octopus.programs import list_programs, load_program

    refs = []
    for name in list_programs():
        program = load_program(name)
        refs.append(ProgramRef(name=program.name, dataset=program.dataset, workspace=program.workspace))
    return tuple(refs)


def _rank(order: Sequence[str], value: str) -> int:
    return order.index(value)


class _Graph:
    """Vue calculée du catalogue : cycles, amont transitif, donnée personnelle et licence effectives.

    Les cycles sont cherchés à la construction ; les calculs transitifs (mémoïsés) exigent
    un graphe acyclique.
    """

    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self.sources = catalog.source_by_id
        self.datasets = catalog.dataset_by_id
        self.cycles = self._find_cycles()
        self.upstream_sources = cache(self._upstream_sources)
        self.personal = cache(self._personal)
        self.research_only = cache(self._research_only)

    def dataset_inputs(self, ds: Dataset) -> tuple[Dataset, ...]:
        if ds.zone == "raw":
            return ()
        return tuple(self.datasets[i] for i in ds.inputs if i in self.datasets)

    def _find_cycles(self) -> tuple[str, ...]:
        found: set[str] = set()
        done: set[str] = set()

        def visit(ds_id: str, stack: tuple[str, ...]) -> None:
            if ds_id in stack:
                found.add(" → ".join((*stack[stack.index(ds_id):], ds_id)))
                return
            ds = self.datasets.get(ds_id)
            if ds_id in done or ds is None:
                return
            for parent in self.dataset_inputs(ds):
                visit(parent.id, (*stack, ds_id))
            done.add(ds_id)

        for ds in self.catalog.datasets:
            visit(ds.id, ())
        return tuple(sorted(found))

    def _acyclic(self) -> None:
        if self.cycles:
            raise ValueError("graphe des jeux cyclique : " + " ; ".join(self.cycles))

    def _upstream_sources(self, ds_id: str) -> frozenset[str]:
        self._acyclic()
        ds = self.datasets.get(ds_id)
        if ds is None:
            return frozenset()
        if ds.zone == "raw":
            return frozenset(i for i in ds.inputs if i in self.sources)
        return frozenset().union(*(self.upstream_sources(p.id) for p in self.dataset_inputs(ds)))

    def _personal(self, ds_id: str) -> tuple[str, bool]:
        """(niveau calculé, identifiant) : max de l'amont, abaissé par l'agrégation ou la minimisation."""
        ds = self.datasets[ds_id]
        identifying = any(self.sources[s].identifying for s in self.upstream_sources(ds_id))
        if ds.zone == "raw":
            levels = [self.sources[s].personal for s in self.upstream_sources(ds_id)]
        else:
            levels = [self.personal(p.id)[0] for p in self.dataset_inputs(ds)]
        level = max(levels, key=lambda p: _rank(PERSONAL, p), default="none")
        if not identifying and ds.aggregated:
            level = "none"
        elif not identifying and ds.minimised and level == "direct":
            level = "indirect"
        return level, identifying

    def _research_only(self, ds_id: str) -> bool:
        """Vrai si déclaré, ou si une source restricted ou un jeu research_only est en amont."""
        self._acyclic()
        ds = self.datasets[ds_id]
        if ds.research_only:
            return True
        if ds.zone == "raw":
            return any(self.sources[s].commercial == "restricted" for s in ds.inputs if s in self.sources)
        return any(self.research_only(p.id) for p in self.dataset_inputs(ds))

    def model_sources(self, model: Model, levels: Iterable[str]) -> frozenset[str]:
        known = (d for d in model.datasets(*levels) if d in self.datasets)
        return frozenset().union(*(self.upstream_sources(d) for d in known))


# --------------------------------------------------------------------------------------------- règles
def _rule_unique_ids(catalog: Catalog) -> list[Issue]:
    issues = []
    for label, items in (("source", catalog.sources), ("jeu", catalog.datasets), ("modèle", catalog.models)):
        seen: set[str] = set()
        for item in items:
            if item.id in seen:
                issues.append(Issue(ERROR, "duplicate_id", item.id, f"identifiant de {label} en double"))
            seen.add(item.id)
    return issues


def _rule_dataset_refs(catalog: Catalog) -> list[Issue]:
    issues, sources, datasets = [], catalog.source_by_id, catalog.dataset_by_id
    for ds in catalog.datasets:
        for ref in ds.inputs:
            if ds.zone == "raw":
                if ref not in sources:
                    issues.append(Issue(ERROR, "ref.unknown", ds.id, f"source inconnue « {ref} »"))
                elif sources[ref].kind == "pretrained":
                    issues.append(Issue(ERROR, "ref.zone", ds.id,
                                        f"« {ref} » est pré-entraîné : il se déclare dans le modèle"))
                continue
            if ref not in datasets:
                issues.append(Issue(ERROR, "ref.unknown", ds.id, f"jeu inconnu « {ref} »"))
            elif datasets[ref].zone not in ALLOWED_INPUT_ZONES[ds.zone]:
                issues.append(Issue(ERROR, "ref.zone", ds.id,
                                    f"un jeu {ds.zone} ne lit pas « {ref} » (zone {datasets[ref].zone})"))
    return issues


def _rule_model_refs(catalog: Catalog) -> list[Issue]:
    issues, datasets, sources = [], catalog.dataset_by_id, catalog.source_by_id
    for m in catalog.models:
        seen: dict[str, str] = {}
        for level in LEVELS:
            for ref in m.data.get(level, ()):
                if ref in seen:
                    issues.append(Issue(ERROR, "ref.level", m.id,
                                        f"« {ref} » cité en {seen[ref]} et en {level}"))
                seen.setdefault(ref, level)
                if ref not in datasets:
                    issues.append(Issue(ERROR, "ref.unknown", m.id, f"jeu inconnu « {ref} »"))
                elif datasets[ref].zone not in MODEL_INPUT_ZONES:
                    issues.append(Issue(ERROR, "ref.zone", m.id,
                                        f"un modèle ne lit jamais un jeu raw (« {ref} »)"))
        for ref in (*m.pretrained, *m.pretrained_research):
            if ref not in sources or sources[ref].kind != "pretrained":
                issues.append(Issue(ERROR, "ref.pretrained", m.id,
                                    f"« {ref} » n'est pas une source pretrained"))
    return issues


def _rule_model_dependencies(catalog: Catalog) -> list[Issue]:
    issues, models = [], catalog.model_by_id
    for m in catalog.models:
        for dep in m.depends_on:
            if dep not in models:
                issues.append(Issue(ERROR, "ref.unknown", m.id, f"modèle amont inconnu « {dep} »"))
            elif _rank(VERSIONS, models[dep].version) > _rank(VERSIONS, m.version):
                issues.append(Issue(ERROR, "availability.depends_on", m.id,
                                    f"« {dep} » arrive en {models[dep].version}, après {m.version}"))

    def visit(node: str, stack: tuple[str, ...]) -> str | None:
        if node in stack:
            return " → ".join((*stack[stack.index(node):], node))
        model = models.get(node)
        for dep in model.depends_on if model else ():
            found = visit(dep, (*stack, node))
            if found:
                return found
        return None

    cycles = {c for c in (visit(m.id, ()) for m in catalog.models) if c}
    issues += [Issue(ERROR, "graph.model_cycle", c.split(" → ")[0], f"dépendances circulaires : {c}")
               for c in sorted(cycles)]
    return issues


def _rule_dataset_cycles(graph: _Graph) -> list[Issue]:
    return [Issue(ERROR, "graph.cycle", c.split(" → ")[0], f"cycle dans les entrées : {c}")
            for c in graph.cycles]


def _rule_personal(graph: _Graph) -> list[Issue]:
    issues = []
    for ds in graph.catalog.datasets:
        level, identifying = graph.personal(ds.id)
        needed = "personnelle" if level == "direct" else "confidentielle" if level == "indirect" else None
        if needed and _rank(CLASSIFICATIONS, ds.classification) < _rank(CLASSIFICATIONS, needed):
            detail = " (voix ou autre contenu identifiant)" if identifying else ""
            issues.append(Issue(ERROR, "personal.classification", ds.id,
                                f"donnée personnelle {level}{detail} : classification ≥ {needed} requise, "
                                f"« {ds.classification} » déclarée"))
    return issues


def _octopus_shape(ds: Dataset, level: str, identifying: bool) -> list[str]:
    policy, problems = ds.octopus.policy, []
    if identifying:
        problems.append("contenu identifiant en amont (voix…) : jamais exporté")
    if ds.zone == "raw":
        problems.append("un jeu raw n'est jamais exporté")
    if not ds.octopus.name:
        problems.append("nom OctOpus (octopus.name) requis")
    if policy == "public":
        if level != "none":
            problems.append(f"public exige aucune donnée personnelle (calculée : {level})")
        if ds.classification not in ("publique", "interne"):
            problems.append(f"public exige une classification publique ou interne ({ds.classification})")
    if policy == "pseudonymised":
        if ds.zone != "features":
            problems.append("pseudonymised réservé à la zone features")
        if level == "direct":
            problems.append("donnée encore directement identifiante après minimisation")
        if not ds.holdout:
            problems.append("holdout: true requis (le holdout reste local, jamais exporté)")
    return problems


def _rule_octopus(graph: _Graph) -> list[Issue]:
    issues, names = [], defaultdict(list)
    for ds in graph.catalog.datasets:
        if ds.octopus.policy == "forbidden":
            continue
        names[ds.octopus.name].append(ds.id)
        shape = _octopus_shape(ds, *graph.personal(ds.id))
        issues += [Issue(ERROR, "octopus.policy", ds.id, p) for p in shape]
        srcs = sorted(graph.upstream_sources(ds.id))
        restricted = [s for s in srcs if graph.sources[s].commercial == "restricted"]
        if restricted:
            issues.append(Issue(ERROR, "octopus.licence", ds.id,
                                f"export interdit : source restricted en amont ({', '.join(restricted)})"))
        pending = [s for s in srcs if graph.sources[s].commercial in ("contract", "unknown")]
        if pending and not ds.octopus.licence_cleared:
            issues.append(Issue(WARNING, "octopus.licence", ds.id,
                                "licence à confirmer avant export (licence_cleared) : " + ", ".join(pending)))
    issues += [Issue(ERROR, "octopus.name", name or "?", f"nom OctOpus partagé par {', '.join(ids)}")
               for name, ids in sorted(names.items(), key=lambda kv: str(kv[0])) if len(ids) > 1]
    return issues


def _rule_licences(graph: _Graph) -> list[Issue]:
    issues = []
    for ds in graph.catalog.datasets:
        if graph.research_only(ds.id) and not ds.research_only:
            issues.append(Issue(ERROR, "licence.research_only", ds.id,
                                "amont non commercial : déclarer research_only: true"))
    pending: dict[str, list[str]] = defaultdict(list)
    for m in graph.catalog.models:
        for ds_id in m.datasets("mandatory", "recommended"):
            if ds_id in graph.datasets and graph.research_only(ds_id):
                issues.append(Issue(ERROR, "licence.research_only", m.id,
                                    f"« {ds_id} » est research_only : optional seulement"))
        for ref in m.pretrained:
            if ref in graph.sources and graph.sources[ref].commercial == "restricted":
                issues.append(Issue(ERROR, "licence.pretrained", m.id,
                                    f"« {ref} » est non commercial : pretrained_research seulement"))
        used = graph.model_sources(m, ("mandatory", "recommended")) | {
            p for p in m.pretrained if p in graph.sources}
        for s in used:
            if graph.sources[s].commercial in ("contract", "unknown"):
                pending[s].append(m.id)
    for s, models in sorted(pending.items()):
        src = graph.sources[s]
        issues.append(Issue(WARNING, "licence.pending", s,
                            f"usage {src.commercial} pour {len(models)} modèle(s) : {', '.join(models)}"))
    return issues


def _rule_availability(graph: _Graph) -> list[Issue]:
    issues = []
    for ds in graph.catalog.datasets:
        parents = graph.dataset_inputs(ds)
        if parents:
            earliest = min((p.available for p in parents), key=lambda v: _rank(VERSIONS, v))
            if _rank(VERSIONS, ds.available) < _rank(VERSIONS, earliest):
                issues.append(Issue(ERROR, "availability.dataset", ds.id,
                                    f"disponible en {ds.available} mais aucune entrée avant {earliest}"))
    for m in graph.catalog.models:
        for ds_id in m.data.get("mandatory", ()):
            ds = graph.datasets.get(ds_id)
            if ds and _rank(VERSIONS, ds.available) > _rank(VERSIONS, m.version):
                issues.append(Issue(ERROR, "availability.model", m.id,
                                    f"jeu obligatoire « {ds_id} » prêt en {ds.available}, après {m.version}"))
    return issues


def _rule_programs(catalog: Catalog, programs: Sequence[ProgramRef]) -> list[Issue]:
    issues, by_name = [], {p.name: p for p in programs}
    exported = {d.octopus.name: d for d in catalog.datasets if d.octopus.policy != "forbidden"}
    for p in programs:
        if p.name.startswith(COMPETITION_PREFIX):
            continue
        ds = exported.get(p.dataset)
        if ds is None or ds.zone != "features":
            issues.append(Issue(ERROR, "program.dataset", p.name,
                                f"jeu « {p.dataset} » absent des jeux features exportables du catalogue"))
            continue
        allowed = SANDBOX_WORKSPACES if ds.octopus.policy == "public" else PRIVATE_WORKSPACES
        if p.workspace not in allowed:
            issues.append(Issue(ERROR, "program.workspace", p.name,
                                f"jeu {ds.octopus.policy} : {' ou '.join(allowed)} attendu ({p.workspace})"))
    used = {m.octopus_program for m in catalog.models if m.octopus_program}
    for m in catalog.models:
        if not m.octopus_program:
            continue
        program = by_name.get(m.octopus_program)
        if program is None:
            issues.append(Issue(ERROR, "program.unknown", m.id,
                                f"programme « {m.octopus_program} » introuvable"))
            continue
        mandatory = {catalog.dataset_by_id[d].octopus.name for d in m.data.get("mandatory", ())
                     if d in catalog.dataset_by_id}
        if program.dataset not in mandatory:
            issues.append(Issue(ERROR, "program.dataset", m.id,
                                f"jeu du programme ({program.dataset}) absent des jeux obligatoires"))
    issues += [Issue(WARNING, "program.unused", p.name, "programme rattaché à aucun modèle du catalogue")
               for p in programs if not p.name.startswith(COMPETITION_PREFIX) and p.name not in used]
    return issues


def _rule_unused(catalog: Catalog) -> list[Issue]:
    read_sources = {i for d in catalog.datasets if d.zone == "raw" for i in d.inputs}
    read_sources |= {p for m in catalog.models for p in (*m.pretrained, *m.pretrained_research)}
    read_datasets = {i for d in catalog.datasets if d.zone != "raw" for i in d.inputs}
    read_datasets |= {d for m in catalog.models for d in m.datasets()}
    issues = [Issue(WARNING, "unused.source", s.id, "source lue par aucun jeu ni modèle")
              for s in catalog.sources if s.id not in read_sources]
    issues += [Issue(WARNING, "unused.dataset", d.id, "jeu lu par aucun jeu ni modèle")
               for d in catalog.datasets if d.id not in read_datasets]
    return issues


def validate(catalog: Catalog, programs: Sequence[ProgramRef] = ()) -> list[Issue]:
    """Applique les neuf règles ; renvoie erreurs puis avertissements, dans un ordre stable."""
    graph = _Graph(catalog)
    issues = [*_rule_unique_ids(catalog), *_rule_dataset_refs(catalog), *_rule_model_refs(catalog),
              *_rule_model_dependencies(catalog), *_rule_dataset_cycles(graph)]
    if not any(i.code == "graph.cycle" for i in issues):
        issues += [*_rule_personal(graph), *_rule_octopus(graph), *_rule_licences(graph),
                   *_rule_availability(graph)]
    issues += [*_rule_programs(catalog, programs), *_rule_unused(catalog)]
    return sorted(issues, key=lambda i: (i.level != ERROR, i.code, i.subject, i.message))


def computed_personal(catalog: Catalog) -> Mapping[str, str]:
    """Niveau de donnée personnelle calculé pour chaque jeu (annexe A2)."""
    graph = _Graph(catalog)
    return MappingProxyType({d.id: graph.personal(d.id)[0] for d in catalog.datasets})


def lineage(catalog: Catalog, model_id: str) -> Lineage:
    """Jeux et sources amont d'un modèle, avec le niveau le plus fort par lequel chacun est atteint."""
    model = catalog.model_by_id.get(model_id)
    if model is None:
        raise KeyError(f"modèle inconnu : {model_id}")
    graph, datasets, sources = _Graph(catalog), {}, {}

    def keep(store: dict[str, str], key: str, level: str) -> None:
        if key not in store or _rank(LEVELS, level) < _rank(LEVELS, store[key]):
            store[key] = level

    def climb(ds_id: str, level: str, seen: frozenset[str]) -> None:
        ds = graph.datasets.get(ds_id)
        if ds is None or ds_id in seen:
            return
        keep(datasets, ds_id, level)
        if ds.zone == "raw":
            for s in ds.inputs:
                keep(sources, s, level)
            return
        for parent in ds.inputs:
            climb(parent, level, seen | {ds_id})

    for level in LEVELS:
        for ds_id in model.data.get(level, ()):
            climb(ds_id, level, frozenset())
    for ref in model.pretrained:
        keep(sources, ref, "mandatory")
    for ref in model.pretrained_research:
        keep(sources, ref, "optional")
    return Lineage(model=model_id, datasets=MappingProxyType(dict(sorted(datasets.items()))),
                   sources=MappingProxyType(dict(sorted(sources.items()))))

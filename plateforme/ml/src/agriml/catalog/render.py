"""Annexes Markdown A1–A4 générées depuis le catalogue (`python -m agriml.catalog render`).

Sortie déterministe (aucun horodatage) : `render --check` compare le rendu aux fichiers du dépôt.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from agriml.catalog.rules import computed_personal, lineage
from agriml.catalog.schema import (
    DOMAINS,
    LEVELS,
    USE_CASES,
    VARIANTS,
    VERSIONS,
    ZONES,
    Catalog,
    Dataset,
    Model,
)

ANNEX_FILES = ("A1_sources.md", "A2_jeux_de_donnees.md", "A3_modeles.md", "A4_matrice.md")
HEADER = ("> Confidentiel - réservé aux partenaires de travail.\n"
          "> Fichier généré par `python -m agriml.catalog render` depuis `ml/catalog/*.yaml` — "
          "ne pas modifier à la main.\n")

DOMAIN_LABELS = {
    "meteo": "Météo et climat", "sols": "Sols", "satellite": "Satellite", "drone": "Drone",
    "iot": "IoT (kit)",
    "phyto": "Phytosanitaire", "agronomie": "Agronomie", "economie": "Économie", "geo": "Géospatial",
    "eau": "Eau et irrigation", "historique": "Historique", "utilisateurs": "Utilisateurs et consentements",
    "langue": "Langue et voix", "connaissances": "Connaissances (RAG)"}
DOMAIN_SHORT = {
    "meteo": "Mét", "sols": "Sol", "satellite": "Sat", "drone": "Dro", "iot": "IoT", "phyto": "Phy",
    "agronomie": "Agr", "economie": "Éco", "geo": "Géo", "eau": "Eau", "historique": "Hist",
    "utilisateurs": "Util", "langue": "Lang", "connaissances": "Conn"}
KIND_LABELS = {
    "public_api": "API publique", "open_data": "Open data", "commercial": "Commercial",
    "partner": "Partenaire",
    "internal": "Interne", "user_input": "Saisie utilisateur", "reference": "Référence",
    "pretrained": "Pré-entraîné"}
COMMERCIAL_LABELS = {"open": "ouvert", "contract": "contrat", "restricted": "non commercial",
                     "unknown": "à vérifier"}
COVERAGE_LABELS = {"full": "complète", "partial": "partielle", "none": "aucune", "unknown": "?"}
PERSONAL_LABELS = {"none": "—", "indirect": "indirecte", "direct": "directe"}
ZONE_LABELS = {"raw": "Zone raw (immuable, jamais exportée)", "curated": "Zone curated (nettoyée, conforme)",
               "features": "Zone features (prête pour l'entraînement)"}
LEVEL_SYMBOLS = {"mandatory": "●", "recommended": "◐", "optional": "○"}
LEVEL_LABELS = {"mandatory": "Obligatoires", "recommended": "Recommandées", "optional": "Optionnelles"}
VARIANT_LABELS = {"competition": "Compétition", "production": "Production", "compromis": "Compromis"}
USE_CASE_LABELS = {
    "IA-1": "Irrigation", "IA-2": "Météo locale", "IA-3": "Vision (photos)",
    "IA-4": "Risques phytosanitaires",
    "IA-5": "Assistant conversationnel", "IA-6": "Fertilisation", "IA-7": "Recommandations",
    "IA-8": "Suivi de culture et rendement", "IA-9": "Finance et assurance",
    "IA-10": "Qualité des données du kit",
    "TRANSVERSE": "Transverse"}
PLATFORMS = (*(f"web:{i}" for i in range(1, 14)), "mobile", "kit", "partner")


def _cell(value: object) -> str:
    """Texte sûr pour une cellule de tableau Markdown (pipes échappés, retours à la ligne aplatis)."""
    text = " ".join(str(value).split()) if value not in (None, "") else "—"
    return text.replace("|", "\\|")


def _table(headers: Iterable[str], rows: Iterable[Iterable[object]]) -> list[str]:
    headers = list(headers)
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(_cell(v) for v in row) + " |" for row in rows]
    return [*lines, ""]


def _grouped(items: Iterable, key: Callable, order: Iterable[str]) -> list[tuple[str, list]]:
    groups: dict[str, list] = defaultdict(list)
    for item in items:
        groups[key(item)].append(item)
    return [(k, groups[k]) for k in order if groups.get(k)]


def _document(title: str, intro: Iterable[str], body: Iterable[str]) -> str:
    return "\n".join([f"# {title}", "", HEADER, *intro, "", *body]).rstrip() + "\n"


# ---------------------------------------------------------------------------------------------- A1
def render_sources(catalog: Catalog) -> str:
    by_domain = _grouped(catalog.sources, lambda s: s.domain, DOMAINS)
    summary = []
    for domain, items in by_domain:
        counts = Counter(s.commercial for s in items)
        summary.append((DOMAIN_LABELS[domain], len(items), *(counts.get(c, 0) for c in COMMERCIAL_LABELS),
                        sum(1 for s in items if s.verified)))
    totals = Counter(s.commercial for s in catalog.sources)
    summary.append(("**Total**", len(catalog.sources), *(totals.get(c, 0) for c in COMMERCIAL_LABELS),
                    sum(1 for s in catalog.sources if s.verified)))
    body = ["## Synthèse", "",
            *_table(["Domaine", "Sources", *COMMERCIAL_LABELS.values(), "Licence vérifiée"], summary)]
    for domain, items in by_domain:
        body += [f"## {DOMAIN_LABELS[domain]}", ""]
        body += _table(["Id", "Source", "Type", "Licence", "Usage commercial", "Perso.",
                        "Couverture SN", "Coût", "Accès", "Vérifiée"],
                       [(f"`{s.id}`", s.name, KIND_LABELS[s.kind], s.licence, COMMERCIAL_LABELS[s.commercial],
                         PERSONAL_LABELS[s.personal] + (" (identifiante)" if s.identifying else ""),
                         COVERAGE_LABELS[s.coverage], s.cost, s.access, s.verified or "non")
                        for s in items])
    intro = [f"{len(catalog.sources)} sources sur {len(by_domain)} domaines. « Usage commercial » : ouvert = "
             "permis ; contrat = accord ou abonnement à signer ; non commercial = recherche seulement ; "
             "à vérifier = licence non confirmée. « Vérifiée » = date de lecture de la licence sur une page "
             "publique (URL dans `sources.yaml`, champ `evidence`)."]
    return _document("Annexe A1 — Sources de données", intro, body)


# ---------------------------------------------------------------------------------------------- A2
def _flags(ds: Dataset) -> str:
    names = (("minimised", "minimisé"), ("aggregated", "agrégé"), ("research_only", "recherche seule"),
             ("holdout", "holdout"))
    return ", ".join(label for attr, label in names if getattr(ds, attr))


def _octopus_label(ds: Dataset) -> str:
    if ds.octopus.policy == "forbidden":
        return "interdit"
    cleared = "" if ds.octopus.licence_cleared else " (licence à confirmer)"
    return f"{ds.octopus.policy} `{ds.octopus.name}`{cleared}"


def render_datasets(catalog: Catalog) -> str:
    personal = computed_personal(catalog)
    zones = Counter(d.zone for d in catalog.datasets)
    policies = Counter(d.octopus.policy for d in catalog.datasets)
    body = ["## Synthèse", "",
            *_table(["Zone", "Jeux"], [(z, zones.get(z, 0)) for z in ZONES]),
            *_table(["Politique OctOpus", "Jeux"], [(p, policies[p]) for p in sorted(policies)])]
    for zone, items in _grouped(catalog.datasets, lambda d: d.zone, ZONES):
        body += [f"## {ZONE_LABELS[zone]}", ""]
        for domain, group in _grouped(items, lambda d: d.domain, DOMAINS):
            body += [f"### {DOMAIN_LABELS[domain]}", ""]
            body += _table(["Id", "Contenu", "Dispo", "Classification", "Perso. calculée", "Entrées",
                            "Grain · rafraîchissement", "Volume", "Rétention", "OctOpus", "Drapeaux"],
                           [(f"`{d.id}`", d.content, d.available, d.classification,
                             PERSONAL_LABELS[personal[d.id]], ", ".join(d.inputs),
                             " · ".join(x for x in (d.grain, d.refresh) if x), d.volume, d.retention,
                             _octopus_label(d), _flags(d)) for d in group])
    intro = [f"{len(catalog.datasets)} jeux du lac `s3://agri-<zone>/<domaine>/<table>/date=AAAA-MM-JJ/`. "
             "La donnée personnelle n'est pas déclarée : elle est calculée depuis les sources amont "
             "(abaissée par la minimisation ou l'agrégation k-anonyme). Seuls les jeux features `public` ou "
             "`pseudonymised` peuvent partir vers OctOpus, en instantané, sans leur holdout."]
    return _document("Annexe A2 — Jeux de données", intro, body)


# ---------------------------------------------------------------------------------------------- A3
def _model_section(catalog: Catalog, m: Model) -> list[str]:
    lines = [f"### `{m.id}` — {m.name}", "",
             f"- **Nature** : {m.kind} · **Version** : {m.version}"
             f" · **Plateformes** : {', '.join(m.platform)}"]
    for level in LEVELS:
        if m.data.get(level):
            lines.append(f"- **Données {LEVEL_LABELS[level].lower()}** : "
                         + ", ".join(f"`{d}`" for d in m.data[level]))
    if m.features:
        lines.append("- **Variables** : " + " ; ".join(m.features))
    extras = (("Pré-entraînés (production)", m.pretrained), ("Pré-entraînés (recherche seulement)",
              m.pretrained_research), ("Modèles amont", m.depends_on))
    lines += [f"- **{label}** : " + ", ".join(f"`{x}`" for x in values) for label, values in extras if values]
    if m.octopus_program:
        lines.append(f"- **Programme OctOpus** : `{m.octopus_program}`")
    secondary = f" ; secondaires : {', '.join(m.metrics.secondary)}" if m.metrics.secondary else ""
    lines += [f"- **Métrique** : {m.metrics.primary} — seuil : {m.metrics.threshold}{secondary}",
              f"- **Entraînement** : {m.training}",
              f"- **Inférence** : {m.inference.mode}"
              + "".join(f" · {x}" for x in (m.inference.latency, m.inference.frequency) if x)
              + f" ; repli : {m.inference.fallback}"]
    sources = lineage(catalog, m.id).sources
    counts = Counter(sources.values())
    per_level = (f"{counts.get(level, 0)} {LEVEL_SYMBOLS[level]}" for level in LEVELS)
    lines.append("- **Sources amont** : " + ", ".join(per_level))
    if m.challenge:
        lines.append(f"- **Point de vigilance** : {m.challenge}")
    lines += ["", *_table(["Variante", "Candidat"], [(VARIANT_LABELS[v], m.candidates[v]) for v in VARIANTS])]
    return lines


def render_models(catalog: Catalog) -> str:
    groups = _grouped(catalog.models, lambda m: m.use_case, USE_CASES)
    body = ["## Synthèse", "",
            *_table(["Id", "Modèle", "Cas d'usage", "Nature", "Version", "Plateformes", "Inférence",
                     "Programme OctOpus"],
                    [(f"`{m.id}`", m.name, m.use_case, m.kind, m.version, ", ".join(m.platform),
                      m.inference.mode, m.octopus_program or "—") for m in catalog.models])]
    for use_case, models in groups:
        body += [f"## {use_case} — {USE_CASE_LABELS[use_case]}", ""]
        for m in models:
            body += _model_section(catalog, m)
    intro = [f"{len(catalog.models)} modèles. Chaque modèle donne ses trois variantes "
             "(compétition, production, compromis), ses données par niveau de nécessité, "
             "sa métrique d'acceptation et son repli. "
             f"Légende des sources amont : {LEVEL_SYMBOLS['mandatory']} obligatoire, "
             f"{LEVEL_SYMBOLS['recommended']} recommandée, {LEVEL_SYMBOLS['optional']} optionnelle."]
    return _document("Annexe A3 — Modèles", intro, body)


# ---------------------------------------------------------------------------------------------- A4
def _domain_levels(catalog: Catalog, m: Model) -> Mapping[str, str]:
    """Niveau le plus fort par domaine de source amont."""
    best: dict[str, str] = {}
    for source_id, level in lineage(catalog, m.id).sources.items():
        domain = catalog.source_by_id[source_id].domain
        if domain not in best or LEVELS.index(level) < LEVELS.index(best[domain]):
            best[domain] = level
    return best


def _source_criticality(catalog: Catalog) -> list[tuple[object, ...]]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for m in catalog.models:
        for source_id, level in lineage(catalog, m.id).sources.items():
            counts[source_id][level] += 1
    rows = []
    for s in catalog.sources:
        c = counts.get(s.id, Counter())
        rows.append((f"`{s.id}`", DOMAIN_LABELS[s.domain], COMMERCIAL_LABELS[s.commercial],
                     *(c.get(level, 0) for level in LEVELS)))
    return sorted(rows, key=lambda r: (-r[3], -r[4], -r[5], r[0]))


def render_matrix(catalog: Catalog) -> str:
    domains = [d for d in DOMAINS if any(s.domain == d for s in catalog.sources)]
    matrix = []
    for m in catalog.models:
        levels = _domain_levels(catalog, m)
        matrix.append((f"`{m.id}`", m.version, *(LEVEL_SYMBOLS.get(levels.get(d), " ") for d in domains)))
    roadmap = []
    for platform in PLATFORMS:
        cells = [", ".join(m.id for m in catalog.models if platform in m.platform and m.version == v)
                 for v in VERSIONS]
        if any(cells):
            roadmap.append((platform, *cells))
    edges = [f"  {dep} --> {m.id}" for m in catalog.models for dep in m.depends_on]
    level_headers = [f"{LEVEL_SYMBOLS[lv]} {LEVEL_LABELS[lv].lower()}" for lv in LEVELS]
    body = ["## A4.1 Modèles × domaines de données", "",
            "Niveau le plus fort par lequel le modèle atteint une source du domaine, via la lignée complète "
            "(jeux curated et features, puis jeux raw, puis sources).", "",
            "Domaines : " + " ; ".join(f"{DOMAIN_SHORT[d]} = {DOMAIN_LABELS[d]}" for d in domains) + ".", "",
            *_table(["Modèle", "Version", *(DOMAIN_SHORT[d] for d in domains)], matrix),
            "## A4.2 Plateformes × versions", "",
            *_table(["Plateforme", *VERSIONS], roadmap),
            "## A4.3 Criticité des sources", "",
            "Nombre de modèles qui atteignent la source, par niveau. Les sources obligatoires "
            "pour beaucoup de modèles et dont l'usage commercial n'est pas « ouvert » sont les "
            "priorités d'acquisition (doc 15).", "",
            *_table(["Source", "Domaine", "Usage commercial", *level_headers],
                    _source_criticality(catalog)),
            "## A4.4 Dépendances entre modèles", "",
            "```mermaid", "flowchart LR", *edges, "```", ""]
    intro = [f"Légende : {LEVEL_SYMBOLS['mandatory']} obligatoire, "
             f"{LEVEL_SYMBOLS['recommended']} recommandé, {LEVEL_SYMBOLS['optional']} optionnel ; "
             "case vide = domaine non utilisé."]
    return _document("Annexe A4 — Matrices de couverture", intro, body)


# ---------------------------------------------------------------------------------------------- écriture
def render_annexes(catalog: Catalog) -> dict[str, str]:
    renderers = (render_sources, render_datasets, render_models, render_matrix)
    return {name: render(catalog) for name, render in zip(ANNEX_FILES, renderers, strict=True)}


def write_annexes(catalog: Catalog, out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in render_annexes(catalog).items():
        path = out / name
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def stale_annexes(catalog: Catalog, out: Path) -> list[str]:
    """Annexes absentes ou différentes du rendu courant (pour `render --check`)."""
    stale = []
    for name, content in render_annexes(catalog).items():
        path = out / name
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            stale.append(name)
    return stale

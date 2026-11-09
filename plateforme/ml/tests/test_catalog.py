"""Catalogue data/IA : schéma, neuf règles de cohérence, lignée, annexes générées et CLI.

Un mini-catalogue synthétique valide sert de base ; chaque cas le modifie pour déclencher une seule règle.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from agriml.catalog import (
    CatalogError,
    ProgramRef,
    computed_personal,
    lineage,
    load_catalog,
    load_program_refs,
    validate,
)
from agriml.catalog import __main__ as cli
from agriml.catalog.render import ANNEX_FILES, HEADER, render_annexes, stale_annexes
from agriml.catalog.schema import ENV_DIR

PROGRAMS = (ProgramRef("need", "need", "agri92-pilot"),
            ProgramRef("competition_x", "x_slug", "agri92-comp-x"))
LICENCE_WARNINGS = {"licence.pending", "octopus.licence"}


def _src(id_: str, domain: str = "meteo", kind: str = "open_data", commercial: str = "open",
         personal: str = "none", **extra) -> dict:
    return {"id": id_, "domain": domain, "kind": kind, "name": f"Source {id_}", "licence": "CC BY 4.0",
            "commercial": commercial, "personal": personal, "coverage": "full", **extra}


def _ds(id_: str, zone: str, inputs: list[str], classification: str = "interne", **extra) -> dict:
    return {"id": id_, "zone": zone, "domain": extra.pop("domain", "meteo"),
            "available": extra.pop("available", "MVP"), "classification": classification, "inputs": inputs,
            "content": f"Jeu {id_}", **extra}


def _model(id_: str, mandatory: list[str], version: str = "V2", **extra) -> dict:
    return {"id": id_, "use_case": "IA-1", "name": f"Modèle {id_}", "kind": "ml", "version": version,
            "platform": ["web:3", "mobile"], "data": {"mandatory": mandatory},
            "candidates": {"competition": "ensemble", "production": "GBM", "compromis": "GBM + règles"},
            "metrics": {"primary": "MAE", "threshold": "<= 1 mm", "secondary": ["biais"]},
            "training": "validation temporelle", "inference": {"mode": "batch", "fallback": "règles FAO-56"},
            **extra}


def _base() -> dict[str, list]:
    """Catalogue minimal valide : météo + comptes (direct, minimisé) → features pseudonymisées → un modèle."""
    return {
        "sources": [_src("wx"), _src("users", domain="utilisateurs", kind="user_input", personal="direct"),
                    _src("backbone", domain="phyto", kind="pretrained")],
        "datasets": [
            _ds("raw.wx", "raw", ["wx"]),
            _ds("raw.users", "raw", ["users"], "personnelle", domain="utilisateurs"),
            _ds("cur.fields", "curated", ["raw.wx", "raw.users"], "confidentielle", minimised=True),
            _ds("feat.need", "features", ["cur.fields"], "confidentielle", holdout=True,
                octopus={"policy": "pseudonymised", "name": "need"}),
        ],
        "models": [_model("need_model", ["feat.need"], pretrained=["backbone"], octopus_program="need")],
    }


def _write(directory: Path, data: dict[str, list]) -> Path:
    for key, entries in data.items():
        text = yaml.safe_dump({key: entries}, allow_unicode=True)
        (directory / f"{key}.yaml").write_text(text, encoding="utf-8")
    return directory


def _issues(tmp_path: Path, data: dict[str, list], programs=PROGRAMS):
    return validate(load_catalog(_write(tmp_path, data)), programs)


def _get(data: dict, kind: str, id_: str) -> dict:
    return next(x for x in data[kind] if x["id"] == id_)


def _ds_of(d: dict, id_: str) -> dict:
    return _get(d, "datasets", id_)


def _m(d: dict, id_: str = "need_model") -> dict:
    return _get(d, "models", id_)


# ------------------------------------------------------------------------------------------- règles
def test_minimal_catalog_is_clean(tmp_path):
    assert _issues(tmp_path, _base()) == []


def _later_dependency(d):
    d["models"].append(_model("later", ["feat.need"], version="V3"))
    _m(d)["depends_on"] = ["later"]


def _model_cycle(d):
    d["models"].append(_model("other", ["feat.need"], depends_on=["need_model"]))
    _m(d)["depends_on"] = ["other"]


def _dataset_cycle(d):
    _ds_of(d, "cur.fields")["inputs"].append("cur.loop")
    d["datasets"].append(_ds("cur.loop", "curated", ["cur.fields"], "confidentielle"))


def _twin_name(d):
    d["datasets"].append(_ds("feat.twin", "features", ["cur.fields"], "confidentielle", holdout=True,
                             octopus={"policy": "pseudonymised", "name": "need"}))
    _m(d)["data"]["optional"] = ["feat.twin"]


def _research_only_mandatory(d):
    _get(d, "sources", "wx")["commercial"] = "restricted"
    for ds_id in ("raw.wx", "cur.fields", "feat.need"):
        _ds_of(d, ds_id)["research_only"] = True


def _not_mandatory_for_model(d):
    _m(d)["data"] = {"mandatory": ["cur.fields"], "optional": ["feat.need"]}


Mutation = Callable[[dict], object]
ERROR_CASES: list[tuple[str, Mutation, str]] = [
    ("duplicate_id", lambda d: d["sources"].append(_src("wx")), "duplicate_id"),
    ("unknown_source", lambda d: _ds_of(d, "raw.wx")["inputs"].append("ghost"), "ref.unknown"),
    ("raw_reads_pretrained", lambda d: _ds_of(d, "raw.wx")["inputs"].append("backbone"), "ref.zone"),
    ("curated_reads_features", lambda d: d["datasets"].append(_ds("cur.bad", "curated", ["feat.need"])),
     "ref.zone"),
    ("unknown_dataset_input", lambda d: _ds_of(d, "cur.fields")["inputs"].append("ghost"), "ref.unknown"),
    ("model_reads_raw", lambda d: _m(d)["data"].update(optional=["raw.wx"]), "ref.zone"),
    ("model_unknown_dataset", lambda d: _m(d)["data"].update(recommended=["ghost"]), "ref.unknown"),
    ("dataset_on_two_levels", lambda d: _m(d)["data"].update(optional=["feat.need"]), "ref.level"),
    ("pretrained_not_pretrained", lambda d: _m(d).update(pretrained=["wx"]), "ref.pretrained"),
    ("unknown_dependency", lambda d: _m(d).update(depends_on=["ghost"]), "ref.unknown"),
    ("later_dependency", _later_dependency, "availability.depends_on"),
    ("model_cycle", _model_cycle, "graph.model_cycle"),
    ("dataset_cycle", _dataset_cycle, "graph.cycle"),
    ("personal_underclassified", lambda d: _ds_of(d, "raw.users").update(classification="interne"),
     "personal.classification"),
    ("not_minimised", lambda d: _ds_of(d, "cur.fields").update(minimised=False), "personal.classification"),
    ("raw_exported", lambda d: _ds_of(d, "raw.wx").update(octopus={"policy": "public", "name": "raw_wx"}),
     "octopus.policy"),
    ("public_with_personal", lambda d: _ds_of(d, "feat.need")["octopus"].update(policy="public"),
     "octopus.policy"),
    ("no_holdout", lambda d: _ds_of(d, "feat.need").update(holdout=False), "octopus.policy"),
    ("pseudonymised_curated", lambda d: _ds_of(d, "cur.fields").update(
        holdout=True, octopus={"policy": "pseudonymised", "name": "cur"}), "octopus.policy"),
    ("missing_octopus_name", lambda d: _ds_of(d, "feat.need")["octopus"].pop("name"), "octopus.policy"),
    ("shared_octopus_name", _twin_name, "octopus.name"),
    ("identifying_exported", lambda d: _get(d, "sources", "users").update(identifying=True),
     "octopus.policy"),
    ("restricted_upstream_export", lambda d: _get(d, "sources", "wx").update(commercial="restricted"),
     "octopus.licence"),
    ("restricted_undeclared", lambda d: _get(d, "sources", "wx").update(commercial="restricted"),
     "licence.research_only"),
    ("research_only_mandatory", _research_only_mandatory, "licence.research_only"),
    ("restricted_pretrained", lambda d: _get(d, "sources", "backbone").update(commercial="restricted"),
     "licence.pretrained"),
    ("dataset_before_inputs",
     lambda d: [_ds_of(d, i).update(available="V2") for i in ("raw.wx", "raw.users")],
     "availability.dataset"),
    ("mandatory_after_model", lambda d: [_ds_of(d, i).update(available="V3")
                                         for i in ("raw.wx", "raw.users", "cur.fields", "feat.need")],
     "availability.model"),
    ("program_unknown", lambda d: _m(d).update(octopus_program="ghost"), "program.unknown"),
    ("program_not_mandatory", _not_mandatory_for_model, "program.dataset"),
]


@pytest.mark.parametrize(("mutate", "code"), [c[1:] for c in ERROR_CASES], ids=[c[0] for c in ERROR_CASES])
def test_each_rule_raises_its_error(tmp_path, mutate, code):
    data = copy.deepcopy(_base())
    mutate(data)
    errors = {i.code for i in _issues(tmp_path, data) if i.level == "error"}
    assert code in errors, errors


@pytest.mark.parametrize(("programs", "code"), [
    ((ProgramRef("need", "ghost", "agri92-pilot"),), "program.dataset"),
    ((ProgramRef("need", "need", "agri92-sandbox"),), "program.workspace"),
])
def test_program_sync_errors(tmp_path, programs, code):
    assert code in {i.code for i in _issues(tmp_path, _base(), programs) if i.level == "error"}


WARNING_CASES: list[tuple[str, Mutation, str]] = [
    ("contract_source", lambda d: _get(d, "sources", "wx").update(commercial="contract"), "licence.pending"),
    ("contract_before_export", lambda d: _get(d, "sources", "wx").update(commercial="unknown"),
     "octopus.licence"),
    ("program_unused", lambda d: _m(d).pop("octopus_program"), "program.unused"),
    ("unused_source", lambda d: d["sources"].append(_src("orphan")), "unused.source"),
    ("unused_dataset", lambda d: d["datasets"].append(_ds("raw.orphan", "raw", ["wx"])), "unused.dataset"),
]


@pytest.mark.parametrize(("mutate", "code"), [c[1:] for c in WARNING_CASES],
                         ids=[c[0] for c in WARNING_CASES])
def test_warnings_do_not_block(tmp_path, mutate, code):
    data = copy.deepcopy(_base())
    mutate(data)
    issues = _issues(tmp_path, data)
    assert [i.code for i in issues if i.level == "error"] == []
    assert code in {i.code for i in issues if i.level == "warning"}


def test_licence_cleared_silences_export_warning_and_research_pretrained_is_allowed(tmp_path):
    data = _base()
    _get(data, "sources", "wx")["commercial"] = "contract"
    _ds_of(data, "feat.need")["octopus"]["licence_cleared"] = True
    _get(data, "sources", "backbone")["commercial"] = "restricted"
    _m(data)["pretrained_research"] = _m(data).pop("pretrained")
    assert {i.code for i in _issues(tmp_path, data)} == {"licence.pending"}


def test_personal_level_is_computed_from_upstream(tmp_path):
    data = _base()
    data["datasets"].append(_ds("cur.stats", "curated", ["raw.users"], "interne", aggregated=True))
    _m(data)["data"]["optional"] = ["cur.stats"]
    personal = computed_personal(load_catalog(_write(tmp_path, data)))
    assert personal["raw.users"] == "direct" and personal["cur.fields"] == "indirect"
    assert personal["cur.stats"] == "none" and personal["raw.wx"] == "none"


def test_identifying_content_is_not_lowered_by_minimisation(tmp_path):
    data = _base()
    _get(data, "sources", "users")["identifying"] = True
    _ds_of(data, "cur.fields")["classification"] = "personnelle"
    assert computed_personal(load_catalog(_write(tmp_path, data)))["cur.fields"] == "direct"


def test_lineage_keeps_strongest_level(tmp_path):
    data = _base()
    _m(data)["data"]["optional"] = ["cur.fields"]
    _m(data)["pretrained_research"] = ["backbone"]
    trace = lineage(load_catalog(_write(tmp_path, data)), "need_model")
    assert set(trace.datasets) == {"cur.fields", "feat.need", "raw.users", "raw.wx"}
    assert set(trace.datasets.values()) == {"mandatory"}
    assert dict(trace.sources) == {"backbone": "mandatory", "users": "mandatory", "wx": "mandatory"}
    with pytest.raises(KeyError):
        lineage(load_catalog(tmp_path), "ghost")


def test_graph_computations_refuse_a_cyclic_catalog(tmp_path):
    data = _base()
    _dataset_cycle(data)
    catalog = load_catalog(_write(tmp_path, data))
    assert [i.code for i in validate(catalog, PROGRAMS)] == ["graph.cycle"]
    with pytest.raises(ValueError, match="cyclique"):
        computed_personal(catalog)


# ------------------------------------------------------------------------------------------- schéma
SCHEMA_CASES: list[tuple[str, Mutation, str]] = [
    ("unknown_field", lambda d: d["sources"][0].update(colour="x"), "champ inconnu « colour »"),
    ("missing_required", lambda d: d["sources"][0].pop("name"), "champ obligatoire « name »"),
    ("missing_inputs", lambda d: d["datasets"][0].pop("inputs"), "champ obligatoire « inputs »"),
    ("bad_enum", lambda d: d["datasets"][0].update(zone="lake"), "« zone »"),
    ("bad_platform", lambda d: d["models"][0].update(platform=["web:14"]), "plateforme"),
    ("bad_verified", lambda d: d["sources"][0].update(verified="1/11/2026"), "« verified »"),
    ("empty_inputs", lambda d: d["datasets"][0].update(inputs=[]), "ne peut pas être vide"),
    ("empty_mandatory", lambda d: d["models"][0].update(data={"mandatory": []}), "data.mandatory"),
    ("flag_not_bool", lambda d: d["datasets"][0].update(holdout="yes"), "true ou false"),
    ("ids_not_list", lambda d: d["models"][0].update(features="ET0"), "liste de textes"),
    ("optional_text_type", lambda d: d["models"][0].update(challenge=3), "texte ou null"),
    ("mapping_type", lambda d: d["models"][0].update(metrics="MAE"), "dictionnaire"),
    ("text_type", lambda d: d["sources"][0].update(licence=3), "texte non vide"),
    ("entry_not_mapping", lambda d: d["sources"].append("wx"), "dictionnaire"),
    ("unknown_variant", lambda d: d["models"][0]["candidates"].update(baseline="x"),
     "champ inconnu « baseline »"),
]


@pytest.mark.parametrize(("mutate", "message"), [c[1:] for c in SCHEMA_CASES],
                         ids=[c[0] for c in SCHEMA_CASES])
def test_schema_problems_are_collected(tmp_path, mutate, message):
    data = copy.deepcopy(_base())
    mutate(data)
    with pytest.raises(CatalogError) as excinfo:
        load_catalog(_write(tmp_path, data))
    assert any(message in p for p in excinfo.value.problems), excinfo.value.problems


def test_file_level_problems(tmp_path):
    _write(tmp_path, _base())
    (tmp_path / "models.yaml").unlink()
    (tmp_path / "sources.yaml").write_text("sources: [unclosed", encoding="utf-8")
    (tmp_path / "datasets.yaml").write_text("jeux: []\n", encoding="utf-8")
    with pytest.raises(CatalogError) as excinfo:
        load_catalog(tmp_path)
    problems = " ".join(excinfo.value.problems)
    assert "fichier absent" in problems and "YAML illisible" in problems and "« datasets »" in problems


def test_catalog_dir_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_DIR, str(_write(tmp_path, _base())))
    assert load_catalog().directory == tmp_path


# ------------------------------------------------------------------------------------------- dépôt
def test_repository_catalog_has_no_errors_and_only_licence_warnings():
    issues = validate(load_catalog(), load_program_refs())
    assert [str(i) for i in issues if i.level == "error"] == []
    assert {i.code for i in issues} <= LICENCE_WARNINGS


def test_repository_restricted_sources_never_reach_production():
    catalog = load_catalog()
    for model in catalog.models:
        for source_id, level in lineage(catalog, model.id).sources.items():
            if catalog.source_by_id[source_id].commercial == "restricted":
                assert level == "optional", (model.id, source_id)


def test_repository_annexes_are_up_to_date():
    assert stale_annexes(load_catalog(), cli.DEFAULT_OUT) == [], "lancer `python -m agriml.catalog render`"


# ------------------------------------------------------------------------------------------- rendu et CLI
def test_render_is_deterministic_and_escapes_pipes(tmp_path):
    data = _base()
    data["sources"][0]["licence"] = "CC BY 4.0 | attribution"
    catalog = load_catalog(_write(tmp_path, data))
    first, second = render_annexes(catalog), render_annexes(catalog)
    assert first == second and tuple(first) == ANNEX_FILES
    assert all(HEADER in text for text in first.values())
    assert "CC BY 4.0 \\| attribution" in first["A1_sources.md"]
    assert "| `need_model` | V2 | ● |" in first["A4_matrice.md"]


@pytest.fixture
def catalog_dir(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(cli, "load_program_refs", lambda: PROGRAMS)
    directory = tmp_path / "catalog"
    directory.mkdir()
    return _write(directory, _base())


def test_cli_check(catalog_dir, capsys):
    assert cli.main(["--dir", str(catalog_dir), "check"]) == 0
    assert "0 erreur(s), 0 avertissement(s)" in capsys.readouterr().out
    data = _base()
    data["sources"].append(_src("orphan"))
    _write(catalog_dir, data)
    assert cli.main(["--dir", str(catalog_dir), "check"]) == 0
    assert cli.main(["--dir", str(catalog_dir), "check", "--strict"]) == 1
    _ds_of(data, "raw.users")["classification"] = "interne"
    _write(catalog_dir, data)
    assert cli.main(["--dir", str(catalog_dir), "check"]) == 1


def test_cli_unreadable_catalog(tmp_path, capsys):
    assert cli.main(["--dir", str(tmp_path), "check"]) == 2
    assert "fichier absent" in capsys.readouterr().err


def test_cli_render_and_check(catalog_dir, tmp_path, capsys):
    out = tmp_path / "annexes"
    assert cli.main(["--dir", str(catalog_dir), "render", "--out", str(out)]) == 0
    assert sorted(p.name for p in out.iterdir()) == sorted(ANNEX_FILES)
    assert cli.main(["--dir", str(catalog_dir), "render", "--out", str(out), "--check"]) == 0
    (out / "A3_modeles.md").write_text("modifié à la main\n", encoding="utf-8")
    assert cli.main(["--dir", str(catalog_dir), "render", "--out", str(out), "--check"]) == 1
    assert "A3_modeles.md" in capsys.readouterr().out
    data = _base()
    _ds_of(data, "feat.need")["holdout"] = False
    _write(catalog_dir, data)
    assert cli.main(["--dir", str(catalog_dir), "render", "--out", str(out)]) == 1


def test_cli_lineage(catalog_dir, capsys):
    assert cli.main(["--dir", str(catalog_dir), "lineage", "need_model"]) == 0
    assert "mandatory (3) : backbone, users, wx" in capsys.readouterr().out
    assert cli.main(["--dir", str(catalog_dir), "lineage", "ghost"]) == 2

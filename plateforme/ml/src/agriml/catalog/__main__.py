"""CLI du catalogue : `python -m agriml.catalog check | render | lineage <modèle>`.

Codes de sortie : 0 = conforme ; 1 = erreurs (ou avertissements avec --strict, ou annexes périmées avec
`render --check`) ; 2 = catalogue illisible ou modèle inconnu.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from agriml.catalog.render import stale_annexes, write_annexes
from agriml.catalog.rules import ERROR, WARNING, lineage, load_program_refs, validate
from agriml.catalog.schema import CATALOG_DIR, LEVELS, CatalogError, load_catalog

DEFAULT_OUT = CATALOG_DIR.parents[1] / "docs" / "annexes"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agriml.catalog", description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, default=None,
                        help="dossier du catalogue (défaut : AGRIML_CATALOG_DIR, sinon ml/catalog)")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="valide le schéma et les neuf règles de cohérence")
    check.add_argument("--strict", action="store_true", help="les avertissements font aussi échouer")
    render = sub.add_parser("render", help="génère les annexes A1–A4")
    render.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help=f"dossier de sortie (défaut : {DEFAULT_OUT})")
    render.add_argument("--check", action="store_true", help="échoue si les annexes du dossier sont périmées")
    trace = sub.add_parser("lineage", help="jeux et sources amont d'un modèle")
    trace.add_argument("model")
    return parser


def _check(catalog, strict: bool) -> int:
    issues = validate(catalog, load_program_refs())
    for issue in issues:
        print(issue)
    errors = sum(1 for i in issues if i.level == ERROR)
    warnings = sum(1 for i in issues if i.level == WARNING)
    print(f"{len(catalog.sources)} sources, {len(catalog.datasets)} jeux, {len(catalog.models)} modèles : "
          f"{errors} erreur(s), {warnings} avertissement(s)")
    return 1 if errors or (strict and warnings) else 0


def _render(catalog, out: Path, check_only: bool) -> int:
    if any(i.level == ERROR for i in validate(catalog, load_program_refs())):
        print("Catalogue en erreur : lancer `check` avant `render`.", file=sys.stderr)
        return 1
    if check_only:
        stale = stale_annexes(catalog, out)
        for name in stale:
            print(f"périmée : {out / name}")
        print("annexes à jour" if not stale else f"{len(stale)} annexe(s) à régénérer")
        return 1 if stale else 0
    for path in write_annexes(catalog, out):
        print(f"écrit : {path}")
    return 0


def _lineage(catalog, model_id: str) -> int:
    try:
        trace = lineage(catalog, model_id)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 2
    for title, items in (("Jeux", trace.datasets), ("Sources", trace.sources)):
        print(f"{title} amont de {model_id} :")
        for level in LEVELS:
            names = [k for k, v in items.items() if v == level]
            if names:
                print(f"  {level} ({len(names)}) : {', '.join(names)}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    try:
        catalog = load_catalog(args.dir)
    except CatalogError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.command == "check":
        return _check(catalog, args.strict)
    if args.command == "render":
        return _render(catalog, args.out, args.check)
    return _lineage(catalog, args.model)


if __name__ == "__main__":
    sys.exit(main())

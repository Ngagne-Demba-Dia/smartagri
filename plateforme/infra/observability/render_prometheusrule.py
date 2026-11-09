"""Génère l'objet PrometheusRule Kubernetes à partir des règles Prometheus de ce dossier.

Les fichiers prometheus/rules/*.yml restent la source unique (utilisés tels quels en local) ;
le fichier généré est versionné dans infra/k8s/base/app/prometheusrules.yaml.

    python infra/observability/render_prometheusrule.py          # régénère le fichier
    python infra/observability/render_prometheusrule.py --check  # échoue s'il est périmé (CI)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
RULES_DIR = HERE / "prometheus" / "rules"
TARGET = HERE.parent / "k8s" / "base" / "app" / "prometheusrules.yaml"
HEADER = (
    "# FICHIER GÉNÉRÉ par infra/observability/render_prometheusrule.py : ne pas modifier à la main.\n"
    "# Source : infra/observability/prometheus/rules/*.yml\n"
)


class _Dumper(yaml.SafeDumper):
    """Écrit les chaînes multilignes (expressions PromQL) en bloc littéral, plus lisible."""


def _str_representer(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str_representer)


def render() -> str:
    groups: list[dict] = []
    for path in sorted(RULES_DIR.glob("*.yml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        groups.extend(document.get("groups", []))
    if not groups:
        raise SystemExit(f"aucun groupe de règles trouvé dans {RULES_DIR}")
    manifest = {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "PrometheusRule",
        "metadata": {
            "name": "smartagri92",
            "labels": {"release": "kube-prometheus-stack"},
        },
        "spec": {"groups": groups},
    }
    body = yaml.dump(manifest, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=120)
    return HEADER + body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Vérifie sans écrire.")
    args = parser.parse_args()
    content = render()
    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != content:
            print(f"{TARGET} est périmé : relancer render_prometheusrule.py", file=sys.stderr)
            return 1
        print("PrometheusRule à jour")
        return 0
    TARGET.write_text(content, encoding="utf-8", newline="\n")
    print(f"écrit : {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

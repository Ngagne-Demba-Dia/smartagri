"""Export d'un paquet de service (bundle) : uniquement ce que `agriml.predict` charge + manifeste + fiche modèle.

Usage : python -m agriml.export --run artifacts/yield_regression --out bundles/yield_regression

Le manifeste liste le SHA-256 de chaque fichier ; `bundle_sha256` (empreinte du manifeste) identifie le paquet
dans le registre MLflow et dans la synchronisation OctOpus. Le service vérifie cette empreinte au chargement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from string import Template
from typing import Any

from agriml import __version__
from agriml.io import git_sha, read_json, sha256_file, write_json
from agriml.logs import setup_logging
from agriml.predict import RunArtifacts, load_run

logger = logging.getLogger("agriml.export")
MANIFEST = "manifest.json"
MODEL_CARD = "MODEL_CARD.md"
RUN_FILES = ("config_resolved.yaml", "ensemble.json", "label_mapping.json", "feature_columns.json", "seeds.json",
             "cv_scores.json", "evaluation.json", "adversarial.json", "meta_model.joblib")
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[2] / "docs" / "model_card_template.md"


class BundleIntegrityError(RuntimeError):
    """Un fichier du paquet ne correspond pas au manifeste."""


def _copy_files(art: RunArtifacts, out_dir: Path) -> list[Path]:
    copied = []
    for name in RUN_FILES:
        src = art.run_dir / name
        if src.exists():
            copied.append(Path(shutil.copy2(src, out_dir / name)))
    for member in art.members:
        dst = out_dir / "models" / member
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted((art.run_dir / "models" / member).glob("*.joblib")):
            copied.append(Path(shutil.copy2(f, dst / f.name)))
    return copied


def build_manifest(out_dir: Path, files: Sequence[Path], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    entries = {f.relative_to(out_dir).as_posix(): {"sha256": sha256_file(f), "bytes": f.stat().st_size}
               for f in sorted(files)}
    return {"files": entries, "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "git_sha": git_sha(out_dir), "agriml_version": __version__, **(extra or {})}


def bundle_sha256(bundle_dir: str | Path) -> str:
    """Empreinte du paquet = SHA-256 de la liste triée (chemin, sha256) du manifeste (indépendante de la date)."""
    files = read_json(Path(bundle_dir) / MANIFEST)["files"]
    canonical = json.dumps({k: v["sha256"] for k, v in sorted(files.items())}, sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def verify_bundle(bundle_dir: str | Path) -> str:
    """Vérifie chaque fichier contre le manifeste ; renvoie l'empreinte du paquet ou lève BundleIntegrityError."""
    bundle_dir = Path(bundle_dir)
    for rel, meta in read_json(bundle_dir / MANIFEST)["files"].items():
        path = bundle_dir / rel
        if not path.exists() or sha256_file(path) != meta["sha256"]:
            raise BundleIntegrityError(f"Fichier altéré ou manquant : {rel}")
    return bundle_sha256(bundle_dir)


def card_context(art: RunArtifacts, manifest: dict[str, Any]) -> dict[str, str]:
    scores = read_json(art.run_dir / "cv_scores.json")
    cfg = art.cfg
    models = scores.get("models", {})
    return {
        "name": cfg.name, "task": cfg.task, "metric": cfg.metric, "created_at": manifest["created_at"],
        "final": f"{art.ensemble['type']} « {art.ensemble['name']} »", "cv_score": f"{art.ensemble['cv']:.5f}",
        "members": ", ".join(art.members), "cv_scheme": f"{cfg.cv.scheme} ({cfg.cv.n_splits} plis)",
        "seeds": ", ".join(map(str, cfg.seeds)), "train_data": str(cfg.data.train),
        "baseline": f"{scores.get('baseline_constant', float('nan')):.5f}",
        "models_table": "\n".join(f"| {n} | {m['cv']:.5f} | {m.get('fold_std', float('nan')):.5f} |"
                                  for n, m in models.items()),
        "holdout": json.dumps(scores.get("holdout", {}), ensure_ascii=False),
        "adversarial_auc": str(scores.get("adversarial_auc")), "git_sha": str(manifest.get("git_sha")),
        "agriml_version": __version__, "threshold": str(art.ensemble.get("threshold")),
    }


def render_model_card(context: dict[str, str], template_path: Path = DEFAULT_TEMPLATE) -> str:
    """Remplit le gabarit ($variables) ; les variables inconnues restent visibles pour être complétées à la main."""
    text = template_path.read_text(encoding="utf-8") if template_path.exists() else "# Fiche modèle $name\n"
    return Template(text).safe_substitute(context)


def export_bundle(run_dir: str | Path, out_dir: str | Path, template_path: Path = DEFAULT_TEMPLATE) -> Path:
    art = load_run(run_dir)
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    files = _copy_files(art, out_dir)
    manifest = build_manifest(out_dir, files, {"experiment": art.cfg.name, "members": art.members})
    card = out_dir / MODEL_CARD
    card.write_text(render_model_card(card_context(art, manifest), template_path), encoding="utf-8")
    manifest["files"][MODEL_CARD] = {"sha256": sha256_file(card), "bytes": card.stat().st_size}
    write_json(manifest, out_dir / MANIFEST)
    logger.info("Paquet %s : %d fichiers, sha256=%s", out_dir, len(manifest["files"]), bundle_sha256(out_dir))
    return out_dir


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export d'un paquet de service agriml.")
    parser.add_argument("--run", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    export_bundle(args.run, args.out, Path(args.template))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

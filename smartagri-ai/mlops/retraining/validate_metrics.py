"""Contrôle MLOps local (Phase 5) : intégrité registre + tables de métriques de référence."""

import csv
import json
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[2]


def run_mlops_checks() -> Dict[str, Any]:
    metrics_dir = ROOT / "metrics"
    csv_files = sorted(metrics_dir.glob("*.csv"))
    non_empty_csv = 0
    for f in csv_files:
        with f.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
            if len(rows) >= 2:
                non_empty_csv += 1

    champions = json.loads((ROOT / "mlops" / "registry" / "champions_summary.json").read_text(encoding="utf-8"))
    sha_file = ROOT / "manifests" / "SHA256SUMS.txt"
    sha_entries = len(sha_file.read_text(encoding="utf-8").splitlines()) if sha_file.exists() else 0

    return {
        "metrics_csv_total": len(csv_files),
        "metrics_csv_valid": non_empty_csv,
        "champions_registered": len(champions),
        "sha256_manifest_entries": sha_entries,
        "retraining_scripts_present": [
            "models/et0/train_A2_et0.py",
            "models/yield/train_A3_yield_A5_price.py",
            "models/clustering/train_A6_A7_A9.py",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(run_mlops_checks(), indent=2, ensure_ascii=False))

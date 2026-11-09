"""Programmes de run OctOpus versionnés (objectif, indices métier, garde-fous, critères d'acceptation).

Un programme = un fichier `programs/<nom>.yaml`. Il alimente :
- l'exporteur (`guardrails` → `PrivacyPolicy`, première barrière) ;
- le lancement du run (`run_request` → corps POST /api/run, à vérifier) et les indices (/hint) ;
- notre porte d'acceptation (`check_acceptance`) : un modèle OctOpus n'est candidat (challenger) que s'il bat
  la référence `agriml` sur le holdout figé, avec une preuve vérifiée et sans surapprentissage manifeste.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from agriml.metrics import get_metric
from agriml.mlops.promotion import improvement
from agriml.octopus.client import RunRequest
from agriml.octopus.exporter import PrivacyPolicy

PROGRAMS_DIR = Path(__file__).resolve().parent / "programs"
TASKS = ("regression", "binary", "multiclass", "image_classification", "forecast")


@dataclass(frozen=True)
class AcceptanceCriteria:
    metric: str
    greater_is_better: bool
    min_relative_gain: float = 0.01          # vs référence agriml, sur le holdout figé
    absolute_threshold: float | None = None  # plancher (ou plafond) métier, ex. MAE ≤ 3 mm
    max_cv_holdout_gap: float = 0.10         # écart relatif CV annoncée / holdout : au-delà, surapprentissage
    max_slice_regression: float = 0.02
    require_proof_verified: bool = True
    human_review: bool = False

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> AcceptanceCriteria:
        data = dict(mapping)
        if "greater_is_better" not in data:
            data["greater_is_better"] = get_metric(data["metric"]).greater_is_better
        return cls(**data)


@dataclass(frozen=True)
class AcceptanceDecision:
    accepted: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class OctopusProgram:
    name: str
    dataset: str
    workspace: str
    task: str
    target: str
    metric: str
    objective: str
    acceptance: AcceptanceCriteria
    guardrails: PrivacyPolicy = field(default_factory=PrivacyPolicy)
    groups: str | None = None
    time_column: str | None = None
    cv: Mapping[str, Any] = field(default_factory=dict)
    time_budget_min: int | None = None
    hints: tuple[str, ...] = ()
    schedule: Mapping[str, Any] | None = None

    def run_request(self, dataset_uri: str) -> RunRequest:
        """Corps du lancement ; les garde-fous sont répétés côté OctOpus (deuxième barrière)."""
        return RunRequest(dataset_uri=dataset_uri, target=self.target, task=self.task, metric=self.metric,
                          objective=self.objective, workspace=self.workspace,
                          time_budget_min=self.time_budget_min, hints=self.hints,
                          guardrails=self.guardrails.to_dict())


def _resolve(name_or_path: str | Path) -> Path:
    path = Path(name_or_path)
    if path.suffix in (".yaml", ".yml") and path.exists():
        return path
    candidate = PROGRAMS_DIR / f"{name_or_path}.yaml"
    if not candidate.exists():
        raise FileNotFoundError(f"Programme OctOpus introuvable : {name_or_path} (voir {PROGRAMS_DIR}).")
    return candidate


def load_program(name_or_path: str | Path) -> OctopusProgram:
    raw = yaml.safe_load(_resolve(name_or_path).read_text(encoding="utf-8")) or {}
    if raw.get("task") not in TASKS:
        raise ValueError(f"Programme {raw.get('name')} : tâche inconnue {raw.get('task')!r} ({', '.join(TASKS)}).")
    acceptance = AcceptanceCriteria.from_mapping({"metric": raw.get("metric"), **raw.pop("acceptance", {})})
    guardrails = PrivacyPolicy.from_mapping(raw.pop("guardrails", {}))
    hints = tuple(str(h).strip() for h in raw.pop("hints", []) or [])
    return OctopusProgram(acceptance=acceptance, guardrails=guardrails, hints=hints, **raw)


def list_programs() -> list[str]:
    return sorted(p.stem for p in PROGRAMS_DIR.glob("*.yaml"))


def _gain_reasons(c: AcceptanceCriteria, holdout_score: float, baseline_score: float | None) -> list[str]:
    reasons = []
    if baseline_score is not None:
        _, rel = improvement(baseline_score, holdout_score, c.greater_is_better)
        if rel < c.min_relative_gain:
            reasons.append(f"gain vs référence agriml {rel:+.2%} < {c.min_relative_gain:.2%}")
    if c.absolute_threshold is not None:
        ok = holdout_score >= c.absolute_threshold if c.greater_is_better else holdout_score <= c.absolute_threshold
        if not ok:
            reasons.append(f"{c.metric} holdout {holdout_score:.5f} hors seuil métier {c.absolute_threshold}")
    return reasons


def check_acceptance(criteria: AcceptanceCriteria, holdout_score: float, baseline_score: float | None,
                     octopus_cv_score: float | None = None, proof_verified: bool | None = None,
                     slice_regressions: Sequence[str] = ()) -> AcceptanceDecision:
    """Porte d'entrée d'un modèle OctOpus (avant la porte champion/challenger de `agriml.mlops.promotion`)."""
    reasons = _gain_reasons(criteria, holdout_score, baseline_score)
    if octopus_cv_score is not None:
        _, rel = improvement(octopus_cv_score, holdout_score, criteria.greater_is_better)
        if rel < -criteria.max_cv_holdout_gap:
            reasons.append(f"holdout {rel:+.1%} vs CV annoncée : surapprentissage ou fuite probable")
    if criteria.require_proof_verified and proof_verified is not True:
        reasons.append("preuve OctOpus non vérifiée (POST /api/proof/verify)")
    reasons += [f"régression sur la tranche {s}" for s in slice_regressions]
    if not reasons and criteria.human_review:
        return AcceptanceDecision(True, ("validation humaine requise avant promotion",))
    return AcceptanceDecision(not reasons, tuple(reasons))

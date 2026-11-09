"""Optimisation d'hyperparamètres : Optuna (TPE + élagage médian) si installé, sinon recherche aléatoire
graine-fixée derrière la même interface.

Espace de recherche (YAML) :
    learning_rate: {type: float, low: 0.01, high: 0.2, log: true}
    max_depth:     {type: int, low: 3, high: 10}
    subsample:     {type: float, low: 0.6, high: 1.0, step: 0.1}
    grow_policy:   {type: categorical, choices: [depthwise, lossguide]}

L'objectif reçoit `report(step, value)` : appelé après chaque pli, il permet d'abandonner un essai
dont les premiers plis sont déjà moins bons que la médiane des essais précédents.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from agriml._optional import optional_import

logger = logging.getLogger(__name__)
MIN_TRIALS_BEFORE_PRUNING = 3

Objective = Callable[[dict[str, Any], Callable[[int, float], None]], float]


class PruneTrial(Exception):
    """Levée par `report` pour abandonner un essai peu prometteur."""


@dataclass(frozen=True)
class TuningResult:
    best_params: dict[str, Any]
    best_score: float
    n_trials: int
    n_pruned: int
    backend: str
    history: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def _sample_random(space: Mapping[str, Mapping], rng: np.random.Generator) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, spec in space.items():
        kind = spec.get("type", "float")
        if kind == "categorical":
            choices = list(spec["choices"])
            params[name] = choices[int(rng.integers(len(choices)))]
        elif kind == "int":
            step = int(spec.get("step", 1))
            if spec.get("log"):
                value = math.exp(rng.uniform(math.log(spec["low"]), math.log(spec["high"])))
                params[name] = int(round(value))
            else:
                params[name] = int(rng.choice(np.arange(spec["low"], spec["high"] + 1, step)))
        else:
            low, high = float(spec["low"]), float(spec["high"])
            value = math.exp(rng.uniform(math.log(low), math.log(high))) if spec.get("log") else rng.uniform(low, high)
            if spec.get("step"):
                value = low + round((value - low) / spec["step"]) * spec["step"]
            params[name] = float(value)
    return params


def _suggest_optuna(trial, space: Mapping[str, Mapping]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for name, spec in space.items():
        kind = spec.get("type", "float")
        if kind == "categorical":
            params[name] = trial.suggest_categorical(name, list(spec["choices"]))
        elif kind == "int":
            params[name] = trial.suggest_int(name, int(spec["low"]), int(spec["high"]),
                                             step=int(spec.get("step", 1)), log=bool(spec.get("log", False)))
        else:
            params[name] = trial.suggest_float(name, float(spec["low"]), float(spec["high"]),
                                               step=spec.get("step"), log=bool(spec.get("log", False)))
    return params


def _tune_optuna(optuna, objective: Objective, space, n_trials, greater, seed, timeout_s) -> TuningResult:
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction="maximize" if greater else "minimize",
        sampler=optuna.samplers.TPESampler(seed=seed),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=MIN_TRIALS_BEFORE_PRUNING),
    )

    def _objective(trial):
        params = _suggest_optuna(trial, space)

        def report(step: int, value: float) -> None:
            trial.report(value, step)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return objective(params, report)

    study.optimize(_objective, n_trials=n_trials, timeout=timeout_s)
    complete = [t for t in study.trials if t.state.name == "COMPLETE"]
    history = tuple({"params": t.params, "score": t.value, "state": t.state.name} for t in study.trials)
    return TuningResult(dict(study.best_params), float(study.best_value), len(complete),
                        len(study.trials) - len(complete), "optuna", history)


class _MedianStopper:
    """Élagage médian minimal : compare la valeur intermédiaire aux médianes des essais terminés."""

    def __init__(self, greater: bool) -> None:
        self.greater = greater
        self.completed: list[dict[int, float]] = []

    def report_fn(self, curve: dict[int, float]) -> Callable[[int, float], None]:
        def report(step: int, value: float) -> None:
            curve[step] = value
            past = [c[step] for c in self.completed if step in c]
            if len(self.completed) < MIN_TRIALS_BEFORE_PRUNING or not past:
                return
            median = float(np.median(past))
            if (value < median) if self.greater else (value > median):
                raise PruneTrial(f"étape {step} : {value:.5f} moins bon que la médiane {median:.5f}")

        return report


def _tune_random(objective: Objective, space, n_trials, greater, seed, timeout_s) -> TuningResult:
    rng = np.random.default_rng(seed)
    stopper = _MedianStopper(greater)
    best_params, best_score = {}, -math.inf if greater else math.inf
    history: list[dict[str, Any]] = []
    n_done = n_pruned = 0
    start = time.monotonic()
    for _ in range(n_trials):
        if timeout_s is not None and time.monotonic() - start > timeout_s:
            break
        params, curve = _sample_random(space, rng), {}
        try:
            score = float(objective(params, stopper.report_fn(curve)))
        except PruneTrial:
            n_pruned += 1
            history.append({"params": params, "score": None, "state": "PRUNED"})
            continue
        stopper.completed.append(curve)
        n_done += 1
        history.append({"params": params, "score": score, "state": "COMPLETE"})
        if (score > best_score) if greater else (score < best_score):
            best_params, best_score = params, score
    return TuningResult(best_params, best_score, n_done, n_pruned, "random", tuple(history))


def tune(objective: Objective, search_space: Mapping[str, Mapping], n_trials: int, greater_is_better: bool,
         seed: int = 42, timeout_s: float | None = None) -> TuningResult:
    """Lance l'optimisation ; renvoie les meilleurs paramètres (à fusionner avec les paramètres fixes)."""
    if not search_space:
        raise ValueError("Espace de recherche vide.")
    optuna = optional_import("optuna")
    if optuna is None:
        logger.info("Optuna non installé : recherche aléatoire graine-fixée (%d essais).", n_trials)
        return _tune_random(objective, search_space, n_trials, greater_is_better, seed, timeout_s)

    def wrapped(params, report):
        try:
            return objective(params, report)
        except PruneTrial as exc:
            raise optuna.TrialPruned() from exc

    return _tune_optuna(optuna, wrapped, search_space, n_trials, greater_is_better, seed, timeout_s)

"""Imports paresseux des dépendances optionnelles (LightGBM, CatBoost, Optuna, MLflow, PyTorch, TensorFlow,
HF, timm, onnx, Airflow, httpx…).

L'absence d'une bibliothèque optionnelle désactive uniquement la fonction concernée,
avec un message clair indiquant l'extra à installer. Rien n'est installé automatiquement.
"""

from __future__ import annotations

import importlib
import logging
from functools import cache
from types import ModuleType

logger = logging.getLogger(__name__)

EXTRAS = {
    "lightgbm": "boosting",
    "catboost": "boosting",
    "optuna": "tuning",
    "mlflow": "tracking",
    "torch": "deep",
    "torchvision": "deep",
    "tensorflow": "deep",
    "keras": "deep",
    "transformers": "vision",
    "timm": "vision",
    "onnx": "vision",
    "onnxruntime": "vision",
    "airflow": "pipelines",
    "httpx": "octopus",
    "nbclient": "notebooks",
}


class OptionalDependencyError(ImportError):
    """Dépendance optionnelle absente."""


@cache
def optional_import(module: str) -> ModuleType | None:
    """Importe un module s'il est installé, sinon renvoie None (résultat mis en cache)."""
    try:
        return importlib.import_module(module)
    except ImportError:
        return None


def is_available(module: str) -> bool:
    return optional_import(module) is not None


def install_hint(module: str) -> str:
    extra = EXTRAS.get(module.split(".")[0])
    return f"pip install 'agriml[{extra}]'" if extra else f"pip install {module}"


def require(module: str, purpose: str) -> ModuleType:
    """Importe un module obligatoire pour `purpose` ou lève une erreur explicite."""
    mod = optional_import(module)
    if mod is None:
        raise OptionalDependencyError(
            f"{purpose} nécessite le paquet « {module} », non installé ({install_hint(module)})."
        )
    return mod

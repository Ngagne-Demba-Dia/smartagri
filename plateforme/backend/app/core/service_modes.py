"""Mode hybride par service : `real` (le backend répond) ou `mock` (la simulation reste en place).

Syntaxe partagée avec le BFF du Frontend (même variable d'environnement, même grammaire) :

    AGRI_MOCK=1                                   # défaut de tous les services : mock (0 → real)
    AGRI_SERVICES=irrigation_need=real,kit_parameters=mock,device_health=mock

`AGRI_SERVICES` ne liste que les exceptions au défaut `AGRI_MOCK`. Les noms sont ceux du doc 16 § 9.3
(18 services) ; `diagnosis_analyze` est accepté comme alias de `disease_diagnosis`. Un nom ou un mode
inconnu fait échouer le démarrage : une faute de frappe ne doit pas laisser un service en simulation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

REAL = "real"
MOCK = "mock"
MODES = frozenset({REAL, MOCK})

SERVICES = (
    "weather", "soil_forecast", "irrigation_need", "irrigation_plan", "recommendations", "fertilization",
    "kit_parameters", "disease_diagnosis", "pest_risk", "trap_counts", "vegetation", "yield_forecast",
    "device_health", "water_savings", "price_forecast", "assistant_chat", "assistant_transcribe", "map_layers",
)
ALIASES = {"diagnosis_analyze": "disease_diagnosis"}
_TRUE = frozenset({"1", "true", "yes", "on"})


class ServiceModeError(ValueError):
    """AGRI_SERVICES invalide."""


def canonical(name: str) -> str:
    key = name.strip()
    key = ALIASES.get(key, key)
    if key not in SERVICES:
        raise ServiceModeError(f"Service inconnu dans AGRI_SERVICES : {name!r}.")
    return key


def parse_overrides(raw: str) -> dict[str, str]:
    """`a=real,b=mock` → {"a": "real", "b": "mock"} (noms ramenés à leur forme canonique)."""
    overrides: dict[str, str] = {}
    for item in filter(None, (part.strip() for part in raw.split(","))):
        name, sep, mode = item.partition("=")
        mode = mode.strip().lower()
        if not sep or mode not in MODES:
            raise ServiceModeError(f"Entrée AGRI_SERVICES invalide : {item!r} (attendu nom=real|mock).")
        overrides[canonical(name)] = mode
    return overrides


@dataclass(frozen=True)
class ServiceModes:
    default: str = REAL
    overrides: Mapping[str, str] = field(default_factory=dict)

    def mode(self, service: str) -> str:
        return self.overrides.get(canonical(service), self.default)

    def is_real(self, service: str) -> bool:
        return self.mode(service) == REAL

    def as_dict(self) -> dict[str, str]:
        return {name: self.mode(name) for name in SERVICES}

    def real_services(self) -> tuple[str, ...]:
        return tuple(name for name in SERVICES if self.is_real(name))


def load_service_modes(env: Mapping[str, str]) -> ServiceModes:
    """Lit AGRI_MOCK (défaut global) et AGRI_SERVICES (exceptions)."""
    default = MOCK if env.get("AGRI_MOCK", "").strip().lower() in _TRUE else REAL
    return ServiceModes(default=default, overrides=parse_overrides(env.get("AGRI_SERVICES", "")))

"""Filtre de verdict ESP32-CAM : transforme une suite de prédictions image par image en un état stable 0/1.

Une image isolée ne déclenche rien : l'alerte (« /plante » etat=1) n'est levée qu'après `n_consecutive`
détections malades consécutives avec une confiance ≥ `confidence_threshold`, et n'est retirée qu'après
`n_consecutive` images saines confiantes (hystérésis : pas de clignotement). Les images incertaines
(confiance < seuil) ne changent pas l'état et remettent les compteurs à zéro.

Valeurs par défaut (0,80 ; 3) = propositions à calibrer sur le terrain (taux de fausses alertes acceptable
par l'agriculteur, cadence de capture). Même règle que le service backend : les deux doivent rester alignés.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

STATE_HEALTHY = 0
STATE_ALERT = 1


@dataclass(frozen=True)
class VerdictConfig:
    confidence_threshold: float = 0.80
    n_consecutive: int = 3
    alert_classes: tuple[str, ...] = ("malade",)
    healthy_classes: tuple[str, ...] = ("sain",)

    def __post_init__(self) -> None:
        if not 0.0 < self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold doit être dans ]0, 1].")
        if self.n_consecutive < 1:
            raise ValueError("n_consecutive doit être ≥ 1.")
        if set(self.alert_classes) & set(self.healthy_classes):
            raise ValueError("Une classe ne peut être à la fois « alerte » et « saine ».")


@dataclass(frozen=True)
class VerdictState:
    """État immuable du filtre (un par caméra / plante)."""

    state: int = STATE_HEALTHY
    alert_streak: int = 0
    healthy_streak: int = 0
    history: tuple[str, ...] = field(default_factory=tuple)

    @property
    def etat(self) -> int:
        """Valeur attendue par l'endpoint firmware « /plante » (0 = sain, 1 = alerte)."""
        return self.state


class EspCamVerdictFilter:
    def __init__(self, config: VerdictConfig = VerdictConfig()):
        self.config = config

    def _classify(self, label: str, confidence: float) -> str:
        if confidence < self.config.confidence_threshold:
            return "incertain"
        if label in self.config.alert_classes:
            return "alerte"
        return "sain" if label in self.config.healthy_classes else "neutre"

    def update(self, state: VerdictState, label: str, confidence: float) -> VerdictState:
        """Renvoie le nouvel état après une prédiction (l'état d'entrée n'est jamais modifié)."""
        kind = self._classify(label, confidence)
        alert = state.alert_streak + 1 if kind == "alerte" else 0
        healthy = state.healthy_streak + 1 if kind == "sain" else 0
        new_state = state.state
        if alert >= self.config.n_consecutive:
            new_state = STATE_ALERT
        elif healthy >= self.config.n_consecutive:
            new_state = STATE_HEALTHY
        history = (*state.history[-(4 * self.config.n_consecutive - 1):], kind)
        return VerdictState(new_state, alert, healthy, history)

    def run(self, predictions: Iterable[tuple[str, float]], state: VerdictState | None = None) -> list[int]:
        """Applique le filtre à une séquence (label, confiance) ; renvoie l'état après chaque image."""
        current = state or VerdictState()
        states = []
        for label, confidence in predictions:
            current = self.update(current, label, confidence)
            states.append(current.etat)
        return states

"""Shared runtime response types (from 82_smartagri_ai_runtime.md)."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class ConfidenceLevel(Enum):
    HIGH = "high"          # >= 0.80
    GOOD = "good"          # >= 0.60
    MODERATE = "moderate"  # >= 0.40
    LOW = "low"            # >= 0.20
    UNRELIABLE = "unreliable"  # < 0.20


@dataclass
class ServiceResponse:
    service: str
    values: Dict[str, Any]
    confidence: float
    confidence_level: ConfidenceLevel
    warnings: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    abstained: bool = False
    abstention_reason: str = ""


def confidence_level(c: float) -> ConfidenceLevel:
    if c >= 0.80:
        return ConfidenceLevel.HIGH
    if c >= 0.60:
        return ConfidenceLevel.GOOD
    if c >= 0.40:
        return ConfidenceLevel.MODERATE
    if c >= 0.20:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.UNRELIABLE

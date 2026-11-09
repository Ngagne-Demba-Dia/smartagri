"""Vocabulaires fermés partagés par l'ORM, les schémas et le SQL de référence (001_init.sql)."""

from __future__ import annotations

ROLES = ("farmer", "coop_manager", "agronomist", "admin")
ORG_KINDS = ("cooperative", "farm", "ngo", "research", "company")
LOCALES = ("fr", "wo", "ff")
IRRIGATION_TYPES = ("drip", "sprinkler", "furrow", "manual")
CROP_CYCLE_STATUSES = ("planned", "active", "harvested", "abandoned")
DEVICE_STATUSES = ("active", "inactive", "retired")
SYNC_STATUSES = ("pending", "sent", "applied", "failed")
TELEMETRY_SOURCES = ("mqtt", "relay", "http")
ALERT_SEVERITIES = ("info", "warning", "critical")
ALERT_STATUSES = ("open", "acknowledged", "resolved")
DIAGNOSIS_LABELS = ("healthy", "suspect", "sick")
RECOMMENDATION_KINDS = ("irrigation", "fertilization")
MESSAGE_ROLES = ("user", "assistant")
RECOMMENDATION_FEEDBACK = ("followed", "partially_followed", "ignored", "not_applicable")
SEASONS = ("dry", "rainy")
CAMPAIGN_STATUSES = ("planned", "active", "closed")
EQUIPMENT_KINDS = ("pump", "tank", "solar_panel", "battery", "sensor", "camera", "gateway", "other")
EQUIPMENT_STATUSES = ("ok", "maintenance", "out_of_service")
MAINTENANCE_KINDS = ("inspection", "preventive", "corrective", "replacement", "other")
MODEL_STAGES = ("none", "staging", "production")
MODEL_SOURCES = ("octopus", "agriml")

SERIAL_PATTERN = r"^SA92-\d{6}$"

# Rôles autorisés par action (contrôle applicatif, voir app/api/deps.py)
FARM_WRITERS = frozenset({"farmer", "coop_manager", "admin"})
DEVICE_WRITERS = frozenset({"coop_manager", "admin"})
THRESHOLD_WRITERS = frozenset({"farmer", "coop_manager", "admin"})
ALERT_ACKERS = frozenset(ROLES)
DIAGNOSIS_WRITERS = frozenset(ROLES)
CAMPAIGN_WRITERS = frozenset({"coop_manager", "admin"})
EQUIPMENT_WRITERS = frozenset({"farmer", "coop_manager", "admin"})
MAINTENANCE_WRITERS = frozenset(ROLES)
FEEDBACK_WRITERS = frozenset({"farmer", "coop_manager", "admin"})
TELEMETRY_WRITERS = frozenset({"farmer", "coop_manager", "admin"})  # envoi par lot via JWT (relais)
CROP_CYCLE_WRITERS = frozenset({"farmer", "coop_manager", "agronomist", "admin"})


def sql_in(column: str, values: tuple[str, ...]) -> str:
    """Expression SQL `col IN ('a','b')` pour une contrainte CHECK (valeurs internes, jamais saisies)."""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"

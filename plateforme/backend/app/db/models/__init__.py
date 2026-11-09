"""Modèles ORM (un module par domaine). L'import enregistre toutes les tables dans `Base.metadata`."""

from app.db.models.assets import Equipment, MaintenanceEvent
from app.db.models.assistant import Conversation, Message
from app.db.models.device import Device, DeviceThreshold
from app.db.models.farm import CropCycle, Farm, Field
from app.db.models.identity import AuditLog, Membership, Organization, RefreshToken, User
from app.db.models.ml import ModelRegistry
from app.db.models.monitoring import Alert, Diagnosis, Image, Measurement, Recommendation
from app.db.models.planning import Campaign, YieldForecast
from app.db.models.weather import WeatherCache

__all__ = [
    "Alert",
    "AuditLog",
    "Campaign",
    "Conversation",
    "CropCycle",
    "Device",
    "DeviceThreshold",
    "Diagnosis",
    "Equipment",
    "Farm",
    "Field",
    "Image",
    "MaintenanceEvent",
    "Measurement",
    "Membership",
    "Message",
    "ModelRegistry",
    "Organization",
    "Recommendation",
    "RefreshToken",
    "User",
    "WeatherCache",
    "YieldForecast",
]

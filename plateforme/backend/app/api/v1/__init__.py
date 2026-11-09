"""Routeur de l'API publique versionnée (/v1)."""

from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    assistant,
    auth,
    campaigns,
    devices,
    diagnoses,
    equipment,
    farms,
    fields,
    reports,
    telemetry,
)

api_router = APIRouter(prefix="/v1")
for _module in (auth, farms, fields, devices, telemetry, alerts, diagnoses, assistant, campaigns, equipment,
                reports):
    api_router.include_router(_module.router)

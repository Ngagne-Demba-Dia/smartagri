"""Exploitations et parcelles : vues JSON, création, localisation et carte GeoJSON d'une exploitation."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import iso_utc
from app.db.models import Alert, CropCycle, Device, Farm, Field
from app.services import geo
from app.services.measurements import latest_measurement

MAP_FIELD_CAP = 500


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float
    source: str  # geometry (centre de la parcelle) | farm (coordonnées de l'exploitation)


def farm_view(farm: Farm) -> dict[str, Any]:
    return {"id": str(farm.id), "organization_id": str(farm.organization_id), "name": farm.name,
            "region": farm.region, "commune": farm.commune, "latitude": farm.latitude,
            "longitude": farm.longitude, "area_ha": farm.area_ha, "created_at": iso_utc(farm.created_at)}


def field_view(field: Field) -> dict[str, Any]:
    centroid = geo.polygon_centroid(field.geometry)
    return {"id": str(field.id), "organization_id": str(field.organization_id), "farm_id": str(field.farm_id),
            "name": field.name, "area_ha": field.area_ha, "soil_type": field.soil_type,
            "irrigation_type": field.irrigation_type, "geometry": field.geometry,
            "centroid": {"longitude": centroid[0], "latitude": centroid[1]} if centroid else None,
            "created_at": iso_utc(field.created_at)}


def create_farm(session: Session, organization_id: uuid.UUID, data: Mapping[str, Any]) -> Farm:
    farm = Farm(organization_id=organization_id, **data)
    session.add(farm)
    session.flush()
    return farm


def create_field(session: Session, farm: Farm, data: Mapping[str, Any]) -> Field:
    values = dict(data)
    if values.get("geometry") is not None:
        values["geometry"] = geo.validate_polygon(values["geometry"])
    field = Field(organization_id=farm.organization_id, farm_id=farm.id, **values)
    session.add(field)
    session.flush()
    return field


def field_location(session: Session, field: Field) -> GeoPoint | None:
    """Centre du contour si connu, sinon coordonnées de l'exploitation, sinon None."""
    centroid = geo.polygon_centroid(field.geometry)
    if centroid is not None:
        return GeoPoint(latitude=centroid[1], longitude=centroid[0], source="geometry")
    farm = session.get(Farm, field.farm_id)
    if farm is not None and farm.latitude is not None and farm.longitude is not None:
        return GeoPoint(latitude=farm.latitude, longitude=farm.longitude, source="farm")
    return None


def active_cycles(session: Session, field_ids: list[uuid.UUID]) -> dict[uuid.UUID, CropCycle]:
    rows = session.scalars(
        select(CropCycle).where(CropCycle.field_id.in_(field_ids), CropCycle.status == "active")
        .order_by(CropCycle.planted_on)
    ).all()
    return {row.field_id: row for row in rows}


def _open_alert_counts(session: Session, field_ids: list[uuid.UUID]) -> tuple[Counter[Any], Counter[Any]]:
    rows = session.execute(
        select(Alert.field_id, Alert.device_id, func.count())
        .where(Alert.field_id.in_(field_ids), Alert.status != "resolved")
        .group_by(Alert.field_id, Alert.device_id)
    ).all()
    by_field: Counter[Any] = Counter()
    by_device: Counter[Any] = Counter()
    for field_id, device_id, count in rows:
        by_field[field_id] += count
        if device_id is not None:
            by_device[device_id] += count
    return by_field, by_device


def _device_feature(session: Session, device: Device, position: tuple[float, float] | None,
                    open_alerts: int) -> dict[str, Any]:
    latest = latest_measurement(session, device.id)
    properties = {"kind": "device", "device_id": str(device.id), "serial": device.serial,
                  "field_id": str(device.field_id) if device.field_id else None, "status": device.status,
                  "soil_moisture_pct": latest.soil_moisture_pct if latest else None,
                  "measured_at": iso_utc(latest.ts) if latest else None,
                  "last_seen_at": iso_utc(device.last_seen_at), "open_alerts": open_alerts,
                  # Le kit n'a pas de GPS : position = centre de sa parcelle (ou de l'exploitation).
                  "position_estimated": True}
    geometry = geo.point(*position) if position else None
    return geo.feature(geometry, properties, f"device:{device.id}")


def farm_map(session: Session, farm: Farm) -> dict[str, Any]:
    """FeatureCollection : contours des parcelles et kits (humidité récente, alertes ouvertes, culture)."""
    fields = session.scalars(
        select(Field).where(Field.farm_id == farm.id).order_by(Field.name).limit(MAP_FIELD_CAP)
    ).all()
    fields_by_id = {f.id: f for f in fields}
    field_ids = list(fields_by_id)
    cycles = active_cycles(session, field_ids)
    alerts_by_field, alerts_by_device = _open_alert_counts(session, field_ids)
    devices = session.scalars(select(Device).where(Device.field_id.in_(field_ids)).order_by(Device.serial)).all()
    farm_position = (farm.longitude, farm.latitude) if farm.latitude is not None and farm.longitude is not None \
        else None
    device_features = []
    soil_by_field: dict[uuid.UUID, float | None] = {}
    for device in devices:
        field = fields_by_id[device.field_id]
        position = geo.polygon_centroid(field.geometry) or farm_position
        item = _device_feature(session, device, position, alerts_by_device.get(device.id, 0))
        soil_by_field.setdefault(field.id, item["properties"]["soil_moisture_pct"])
        device_features.append(item)
    field_features = [
        geo.feature(field.geometry, {
            "kind": "field", "field_id": str(field.id), "name": field.name, "area_ha": field.area_ha,
            "crop": cycles[field.id].crop if field.id in cycles else None,
            "soil_moisture_pct": soil_by_field.get(field.id), "open_alerts": alerts_by_field.get(field.id, 0),
        }, f"field:{field.id}")
        for field in fields
    ]
    collection = geo.feature_collection(field_features + device_features)
    collection["properties"] = {"farm_id": str(farm.id), "name": farm.name}
    return collection

"""SIG : validation des contours GeoJSON et construction des cartes (FeatureCollection).

Les contours sont des polygones GeoJSON (RFC 7946, WGS 84, ordre longitude/latitude). Sous PostgreSQL la
colonne PostGIS `fields.geom` est générée depuis ce GeoJSON (001_init.sql) ; sous SQLite seul le texte JSON
existe. La validation applicative s'applique dans les deux cas, avant toute écriture.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

MAX_VERTICES = 1000
MIN_RING_POSITIONS = 4


class GeometryError(ValueError):
    """Contour GeoJSON invalide (message en français, renvoyé tel quel au client en 422)."""


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise GeometryError("Chaque coordonnée doit être un nombre fini.")
    return float(value)


def _position(raw: Any) -> list[float]:
    if not isinstance(raw, Sequence) or isinstance(raw, str) or len(raw) not in (2, 3):
        raise GeometryError("Une position GeoJSON est [longitude, latitude] (altitude facultative).")
    lon, lat = _number(raw[0]), _number(raw[1])
    if not -180 <= lon <= 180:
        raise GeometryError(f"Longitude hors plage [-180, 180] : {lon}.")
    if not -90 <= lat <= 90:
        raise GeometryError(f"Latitude hors plage [-90, 90] : {lat}.")
    return [lon, lat]


def _ring(raw: Any) -> list[list[float]]:
    if not isinstance(raw, Sequence) or isinstance(raw, str):
        raise GeometryError("Un anneau doit être une liste de positions.")
    positions = [_position(item) for item in raw]
    if len(positions) < MIN_RING_POSITIONS:
        raise GeometryError("Un anneau compte au moins 4 positions (la première répétée à la fin).")
    if positions[0] != positions[-1]:
        raise GeometryError("Anneau non fermé : la dernière position doit être identique à la première.")
    if len({tuple(p) for p in positions[:-1]}) < MIN_RING_POSITIONS - 1:
        raise GeometryError("Anneau dégénéré : au moins 3 sommets distincts sont nécessaires.")
    return positions


def validate_polygon(geometry: Mapping[str, Any]) -> dict[str, Any]:
    """Valide un polygone GeoJSON et renvoie une copie normalisée (flottants, altitude supprimée)."""
    if not isinstance(geometry, Mapping) or geometry.get("type") != "Polygon":
        raise GeometryError("Le contour doit être un objet GeoJSON de type « Polygon ».")
    rings_raw = geometry.get("coordinates")
    if not isinstance(rings_raw, Sequence) or isinstance(rings_raw, str) or not rings_raw:
        raise GeometryError("« coordinates » doit contenir au moins un anneau extérieur.")
    if sum(len(r) for r in rings_raw if isinstance(r, Sequence)) > MAX_VERTICES:
        raise GeometryError(f"Contour trop détaillé : {MAX_VERTICES} sommets au maximum.")
    return {"type": "Polygon", "coordinates": [_ring(ring) for ring in rings_raw]}


def polygon_centroid(geometry: Mapping[str, Any] | None) -> tuple[float, float] | None:
    """Centre approché (moyenne des sommets de l'anneau extérieur) : suffisant pour une parcelle."""
    if not geometry or geometry.get("type") != "Polygon":
        return None
    outer = geometry.get("coordinates", [[]])[0]
    vertices = outer[:-1] if len(outer) > 1 else outer
    if not vertices:
        return None
    lon = sum(p[0] for p in vertices) / len(vertices)
    lat = sum(p[1] for p in vertices) / len(vertices)
    return round(lon, 6), round(lat, 6)


def point(lon: float, lat: float) -> dict[str, Any]:
    return {"type": "Point", "coordinates": [lon, lat]}


def feature(geometry: Mapping[str, Any] | None, properties: Mapping[str, Any], feature_id: str) -> dict[str, Any]:
    return {"type": "Feature", "id": feature_id, "geometry": dict(geometry) if geometry else None,
            "properties": dict(properties)}


def feature_collection(features: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": [dict(item) for item in features]}

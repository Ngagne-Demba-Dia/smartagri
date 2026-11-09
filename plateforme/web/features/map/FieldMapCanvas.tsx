"use client";

import "leaflet/dist/leaflet.css";

import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { CircleMarker, MapContainer, Polygon, ScaleControl, Tooltip, useMap } from "react-leaflet";

import { MISSING, formatNumber, formatPct } from "@/lib/format";
import {
  fieldClass,
  kitClass,
  type FarmMapShapes,
  type LatLonBounds,
  type MapFieldShape,
  type MapMode,
} from "@/lib/map-style";

const FIT_PADDING: [number, number] = [24, 24];
const MAX_FIT_ZOOM = 17;
const KIT_RADIUS_PX = 7;

export interface FieldMapCanvasProps {
  shapes: FarmMapShapes;
  mode: MapMode;
  showKits: boolean;
  showBoundaries: boolean;
  selectedId: string | null;
  onSelect: (fieldId: string) => void;
}

/**
 * Recadre la carte quand l'emprise change (autre exploitation). Dépendances numériques : un rafraîchissement
 * des données à géométrie égale ne défait pas le zoom choisi.
 */
function FitBounds({ bounds }: { bounds: LatLonBounds }) {
  const map = useMap();
  const [[south, west], [north, east]] = bounds;
  useEffect(() => {
    map.fitBounds(
      [
        [south, west],
        [north, east],
      ],
      { padding: FIT_PADDING, maxZoom: MAX_FIT_ZOOM },
    );
  }, [map, south, west, north, east]);
  return null;
}

/** Valeur du mode courant pour l'infobulle et l'étiquette ; jamais de pourcentage de confiance ici. */
function useModeValue() {
  const t = useTranslations("map.canvas");
  return (mode: MapMode, field: MapFieldShape): string => {
    const p = field.props;
    if (mode === "moisture") return t("moisture", { value: formatPct(p.soil_moisture_pct) });
    if (mode === "ndvi") return t("ndvi", { value: p.ndvi === null ? MISSING : formatNumber(p.ndvi, 2) });
    if (mode === "salinity")
      return t("salinity", { value: p.salinity_class ? t(`salinityClass.${p.salinity_class}`) : MISSING });
    if (!p.crop_type) return t("cropPending");
    return p.crop_type.probability === null
      ? t("cropUncertain")
      : t("cropDetected", { label: p.crop_type.label });
  };
}

/**
 * Fond Leaflet sans tuiles (aucune requête externe, CSP 'self') : polygones des parcelles colorés selon le mode,
 * contours de la couche field_boundary en pointillé, kits en cercles. Chargé côté client seulement (next/dynamic).
 * Les classes changent avec le mode et la sélection : Leaflet ne relit pas className après création,
 * d'où la clé qui recrée le tracé.
 */
export default function FieldMapCanvas({
  shapes,
  mode,
  showKits,
  showBoundaries,
  selectedId,
  onSelect,
}: FieldMapCanvasProps) {
  const t = useTranslations("map.canvas");
  const modeValue = useModeValue();
  const bounds = shapes.bounds;
  if (!bounds) return null;
  const names = new Map(shapes.fields.map((f) => [f.props.field_id, f.props.name]));

  return (
    <MapContainer
      bounds={bounds}
      boundsOptions={{ padding: FIT_PADDING, maxZoom: MAX_FIT_ZOOM }}
      className="h-[60vh] min-h-[320px] w-full rounded-card border border-line"
      attributionControl={false}
      scrollWheelZoom={false}
    >
      <FitBounds bounds={bounds} />
      <ScaleControl position="bottomleft" imperial={false} />
      {shapes.fields.map((field) => {
        const id = field.props.field_id;
        const className = fieldClass(mode, field.props, id === selectedId);
        if (field.polygons.length === 0) return null;
        return (
          <Polygon
            key={`${id}:${className}`}
            positions={field.polygons}
            pathOptions={{ className }}
            eventHandlers={{ click: () => onSelect(id) }}
          >
            <Tooltip
              key={`${id}:${mode}`}
              permanent={mode === "crop"}
              direction="center"
              className={mode === "crop" ? "map-label" : "map-tooltip"}
            >
              <strong>{field.props.name}</strong>
              <br />
              {modeValue(mode, field)}
            </Tooltip>
          </Polygon>
        );
      })}
      {showBoundaries
        ? shapes.fields.flatMap((field) =>
            (field.boundary ?? []).map((polygon, i) => (
              <Polygon
                key={`bnd:${field.props.field_id}:${i}`}
                positions={polygon}
                pathOptions={{ className: "map-boundary" }}
                interactive={false}
              />
            )),
          )
        : null}
      {showKits
        ? shapes.kits.map((kit) =>
            kit.position ? (
              <CircleMarker
                key={`${kit.props.device_id}:${kitClass(kit.props)}`}
                center={kit.position}
                radius={KIT_RADIUS_PX}
                pathOptions={{ className: kitClass(kit.props) }}
                eventHandlers={{ click: () => kit.props.field_id && onSelect(kit.props.field_id) }}
              >
                <Tooltip className="map-tooltip" direction="top">
                  <strong>{kit.props.serial}</strong>
                  <br />
                  {t("kitField", {
                    field: kit.props.field_id ? (names.get(kit.props.field_id) ?? MISSING) : MISSING,
                  })}
                  <br />
                  {t("moisture", { value: formatPct(kit.props.soil_moisture_pct) })}
                  {kit.props.position_estimated ? (
                    <>
                      <br />
                      {t("kitEstimated")}
                    </>
                  ) : null}
                </Tooltip>
              </CircleMarker>
            ) : null,
          )
        : null}
    </MapContainer>
  );
}

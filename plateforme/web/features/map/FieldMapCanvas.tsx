"use client";

import "leaflet/dist/leaflet.css";

import { useTranslations } from "next-intl";
import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Polygon, Polyline, ScaleControl, Tooltip, useMap } from "react-leaflet";

import { MISSING, formatNumber, formatPct } from "@/lib/format";
import {
  boundsOf,
  fieldClass,
  kitClass,
  labelPoint,
  ndviStep,
  type FarmMapShapes,
  type LatLon,
  type LatLonBounds,
  type MapFieldShape,
  type MapMode,
} from "@/lib/map-style";
import {
  SENEGAL_BORDER,
  SENEGAL_BOUNDS,
  SENEGAL_FIELD_SPOTS,
  SENEGAL_RIVERS,
  SENEGAL_ZONES,
  type AgroZoneId,
  type RegionalFieldSpot,
} from "@/lib/senegal-geo";
import { moistureRamp } from "@/lib/status";

const FIT_PADDING: [number, number] = [28, 28];
const MAX_FIT_ZOOM = 18;
const KIT_RADIUS_PX = 9;
const KIT_HALO_PX = 16;

export type MapScope = "senegal" | "farm";

export interface FieldMapCanvasProps {
  shapes: FarmMapShapes;
  allFields?: ReadonlyMap<string, MapFieldShape>;
  scope?: MapScope;
  activeZone?: AgroZoneId | "all";
  mode: MapMode;
  showKits: boolean;
  showBoundaries: boolean;
  showHydraulic?: boolean;
  selectedId: string | null;
  onSelect: (fieldId: string) => void;
  onZoneSelect?: (zoneId: AgroZoneId) => void;
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

function RecenterControl({ bounds, label }: { bounds: LatLonBounds; label: string }) {
  const map = useMap();
  return (
    <div className="leaflet-top leaflet-left !top-20">
      <div className="leaflet-control">
        <button
          type="button"
          className="glass glass-strong rounded-btn px-2.5 py-1.5 text-xs font-semibold text-ink shadow-sm hover:bg-surface"
          onClick={() => map.fitBounds(bounds, { padding: FIT_PADDING, maxZoom: MAX_FIT_ZOOM })}
        >
          {label}
        </button>
      </div>
    </div>
  );
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
    if (!p.crop_type) return p.crop ? `${p.crop}` : t("cropPending");
    return p.crop_type.probability === null
      ? t("cropUncertain")
      : t("cropDetected", { label: p.crop_type.label });
  };
}

/** Calcule le cadre cadastral de l'exploitation, la position de la station de pompage et les conduites d'eau. */
function buildInfrastructure(bounds: LatLonBounds, fields: readonly MapFieldShape[]) {
  const [[south, west], [north, east]] = bounds;
  const latSpan = Math.max(north - south, 0.0012);
  const lonSpan = Math.max(east - west, 0.0012);
  const padLat = latSpan * 0.18;
  const padLon = lonSpan * 0.18;

  const domainFrame: LatLon[] = [
    [south - padLat, west - padLon],
    [south - padLat, east + padLon],
    [north + padLat, east + padLon],
    [north + padLat, west - padLon],
  ];

  const pumpStation: LatLon = [north + padLat * 0.45, (west + east) / 2];
  const pipes: LatLon[][] = fields
    .map((f) => labelPoint(f.polygons))
    .filter((pt): pt is LatLon => pt !== null)
    .map((center) => [pumpStation, [pumpStation[0], center[1]], center]);

  const centerCoord: LatLon = [(south + north) / 2, (west + east) / 2];
  return { domainFrame, pumpStation, pipes, centerCoord };
}

/** Couleur d'un champ sur la carte nationale selon le mode choisi. */
function spotFillClass(mode: MapMode, spot: RegionalFieldSpot, selected: boolean): string {
  const step = mode === "ndvi" ? ndviStep(spot.ndvi) : moistureRamp(spot.moisturePct);
  const fill = mode === "crop" ? "map-fill-3" : step === 0 ? "map-fill-0" : `map-fill-${step}`;
  return `map-field ${fill}${selected ? " map-selected" : ""}`;
}

function spotLabelValue(
  t: ReturnType<typeof useTranslations<"map.canvas">>,
  mode: MapMode,
  spot: RegionalFieldSpot,
): string {
  if (mode === "moisture") return t("moisture", { value: formatPct(spot.moisturePct) });
  if (mode === "ndvi") return t("ndvi", { value: formatNumber(spot.ndvi, 2) });
  if (mode === "salinity") return `pH ${formatNumber(spot.ph, 1)}`;
  return spot.crop;
}

/**
 * Fond Leaflet :
 * - En mode `scope === "senegal"` (par défaut) : carte nationale du Sénégal, ses 6 zones agro-écologiques,
 *   les fleuves (Sénégal, Lac de Guiers, Casamance, Gambie) et les champs répartis dans chaque zone.
 * - En mode `scope === "farm"` : vue cadastrale détaillée du périmètre choisi et de son réseau hydraulique.
 */
export default function FieldMapCanvas({
  shapes,
  allFields,
  scope = "senegal",
  activeZone = "all",
  mode,
  showKits,
  showBoundaries,
  showHydraulic = true,
  selectedId,
  onSelect,
  onZoneSelect,
}: FieldMapCanvasProps) {
  const t = useTranslations("map.canvas");
  const modeValue = useModeValue();

  const targetBounds = useMemo<LatLonBounds | null>(() => {
    if (scope === "senegal") {
      if (activeZone !== "all") {
        const zone = SENEGAL_ZONES.find((z) => z.id === activeZone);
        if (zone) return boundsOf(zone.polygon) ?? SENEGAL_BOUNDS;
      }
      return SENEGAL_BOUNDS;
    }
    return shapes.bounds;
  }, [scope, activeZone, shapes.bounds]);

  const infra = useMemo(
    () => (shapes.bounds ? buildInfrastructure(shapes.bounds, shapes.fields) : null),
    [shapes.bounds, shapes.fields],
  );

  const enrichedSpots = useMemo(() => {
    return SENEGAL_FIELD_SPOTS.filter((s) => activeZone === "all" || s.zoneId === activeZone).map((spot) => {
      const live = allFields?.get(spot.id)?.props;
      if (!live) return spot;
      return {
        ...spot,
        crop: live.crop ?? spot.crop,
        areaHa: live.area_ha ?? spot.areaHa,
        moisturePct: live.soil_moisture_pct ?? spot.moisturePct,
        ndvi: live.ndvi ?? spot.ndvi,
      };
    });
  }, [allFields, activeZone]);

  if (!targetBounds) return null;
  const names = new Map(shapes.fields.map((f) => [f.props.field_id, f.props.name]));
  const centerCoord: LatLon =
    scope === "senegal" ? [14.5, -14.45] : (infra?.centerCoord ?? [15.14, -16.88]);

  return (
    <div className="relative isolate">
      <MapContainer
        bounds={targetBounds}
        boundsOptions={{ padding: FIT_PADDING, maxZoom: scope === "senegal" ? 11 : MAX_FIT_ZOOM }}
        className="h-[64vh] min-h-[420px] w-full rounded-card border border-line shadow-sm"
        attributionControl={false}
        scrollWheelZoom={false}
      >
        <FitBounds bounds={targetBounds} />
        <RecenterControl bounds={targetBounds} label={t("recenter")} />
        <ScaleControl position="bottomleft" imperial={false} />

        {scope === "senegal" ? (
          <>
            <Polygon
              positions={SENEGAL_BORDER as LatLon[]}
              pathOptions={{ className: "map-senegal-border" }}
              interactive={false}
            />

            {SENEGAL_ZONES.map((zone) => {
              const isSelectedZone = activeZone === zone.id;
              return (
                <Polygon
                  key={zone.id}
                  positions={zone.polygon as LatLon[]}
                  pathOptions={{
                    className: `${zone.className}${isSelectedZone ? " map-zone-selected" : ""}`,
                  }}
                  eventHandlers={{
                    click: () => onZoneSelect?.(zone.id),
                  }}
                >
                  <Tooltip permanent direction="center" className="map-label">
                    <strong>{zone.name}</strong>
                    <br />
                    <span className="text-xs">{zone.crops}</span>
                  </Tooltip>
                </Polygon>
              );
            })}

            {SENEGAL_RIVERS.map((river) => (
              <Polyline
                key={river.id}
                positions={river.path as LatLon[]}
                pathOptions={{ className: "map-river" }}
                interactive={false}
              />
            ))}

            {enrichedSpots.map((spot) => {
              const isSel = spot.id === selectedId;
              return (
                <CircleMarker
                  key={`${spot.id}:${mode}:${isSel}`}
                  center={spot.position}
                  radius={isSel ? 13 : 10}
                  pathOptions={{ className: spotFillClass(mode, spot, isSel) }}
                  eventHandlers={{ click: () => onSelect(spot.id) }}
                >
                  <Tooltip permanent={isSel || activeZone !== "all"} direction="top" className="map-label">
                    <strong>{spot.name}</strong>
                    <br />
                    {spot.crop} · {formatNumber(spot.areaHa, 1)} ha
                    <br />
                    {spotLabelValue(t, mode, spot)} · Kit {spot.kitSerial}
                  </Tooltip>
                </CircleMarker>
              );
            })}
          </>
        ) : (
          <>
            {infra ? (
              <Polygon positions={infra.domainFrame} pathOptions={{ className: "map-domain-frame" }} interactive={false} />
            ) : null}

            {showHydraulic && infra
              ? infra.pipes.map((pipe, idx) => (
                  <Polyline key={`pipe:${idx}`} positions={pipe} pathOptions={{ className: "map-pipe" }} interactive={false} />
                ))
              : null}

            {showHydraulic && infra ? (
              <CircleMarker
                center={infra.pumpStation}
                radius={8}
                pathOptions={{ className: "map-pump-station" }}
                interactive={false}
              >
                <Tooltip permanent direction="top" className="map-label">
                  <strong>{t("pumpStation")}</strong>
                </Tooltip>
              </CircleMarker>
            ) : null}

            {shapes.fields.map((field) => {
              const id = field.props.field_id;
              const className = fieldClass(mode, field.props, id === selectedId);
              if (field.polygons.length === 0) return null;
              const areaText = field.props.area_ha !== null ? ` · ${formatNumber(field.props.area_ha, 1)} ha` : "";
              const cropText = field.props.crop ? ` (${field.props.crop}${areaText})` : areaText;
              return (
                <Polygon
                  key={`${id}:${className}`}
                  positions={field.polygons}
                  pathOptions={{ className }}
                  eventHandlers={{ click: () => onSelect(id) }}
                >
                  <Tooltip key={`${id}:${mode}`} permanent direction="center" className="map-label">
                    <strong>
                      {field.props.name}
                      {cropText}
                    </strong>
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
                      key={`halo:${kit.props.device_id}`}
                      center={kit.position}
                      radius={KIT_HALO_PX}
                      pathOptions={{ className: "map-kit-halo" }}
                      interactive={false}
                    />
                  ) : null,
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
          </>
        )}
      </MapContainer>

      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-3 top-3 z-[400] flex items-center gap-2 rounded-btn border border-glass-edge bg-[var(--glass-strong)] px-3 py-1.5 text-xs font-semibold text-ink shadow-sm backdrop-blur"
      >
        <span>{scope === "senegal" ? "🇸🇳 Sénégal" : "▲ N"}</span>
        <span className="text-mute">·</span>
        <span className="tabular-nums">
          {formatNumber(Math.abs(centerCoord[0]), 4)}° N, {formatNumber(Math.abs(centerCoord[1]), 4)}° O
        </span>
      </div>
    </div>
  );
}

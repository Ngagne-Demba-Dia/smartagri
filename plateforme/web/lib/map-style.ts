/**
 * Carte Leaflet (module 4, service 18 map_layers) : fonctions pures, sans dépendance à Leaflet.
 * - GeoJSON [lon, lat] → positions Leaflet [lat, lon] ;
 * - fusion de la carte de base (route existante) et de la couche demandée (route proposée) ;
 * - pas de couleur par mode (humidité, NDVI, culture, salinité) et légende associée.
 * Les couleurs viennent des jetons --ramp-1…5 (app/globals.css) par des classes : jamais d'attribut style.
 */
import type { MapFeatureView, MapLayer, MapLayersView } from "@/lib/contracts/org";
import { moistureRamp, type RampStep } from "@/lib/status";

/** Position Leaflet [latitude, longitude] (compatible avec L.LatLngTuple). */
export type LatLon = [number, number];
/** Un polygone : anneau extérieur puis trous éventuels. */
export type PolygonRings = LatLon[][];

type FeatureProps = MapFeatureView["properties"];
export type FieldProps = Extract<FeatureProps, { kind: "field" }>;
export type DeviceProps = Extract<FeatureProps, { kind: "device" }>;
export type SalinityClass = NonNullable<FieldProps["salinity_class"]>;

/* ---------- Géométrie ---------- */

const isNumber = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

/** [lon, lat] GeoJSON → [lat, lon] ; null si la paire est illisible ou hors des bornes terrestres. */
export function toLatLon(position: unknown): LatLon | null {
  if (!Array.isArray(position) || position.length < 2) return null;
  const [lon, lat] = position as unknown[];
  if (!isNumber(lon) || !isNumber(lat)) return null;
  if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return [lat, lon];
}

const MIN_RING_POINTS = 3;

function ringOf(raw: unknown): LatLon[] | null {
  if (!Array.isArray(raw)) return null;
  const ring = raw.map(toLatLon);
  if (ring.some((p) => p === null)) return null;
  return ring.length >= MIN_RING_POINTS ? (ring as LatLon[]) : null;
}

function polygonOf(raw: unknown): PolygonRings | null {
  if (!Array.isArray(raw) || raw.length === 0) return null;
  const rings = raw.map(ringOf);
  return rings.every((r): r is LatLon[] => r !== null) ? rings : null;
}

/** Polygon ou MultiPolygon → liste de polygones ; liste vide pour toute autre géométrie ou une géométrie illisible. */
export function polygonsOf(geometry: MapFeatureView["geometry"]): PolygonRings[] {
  if (!geometry) return [];
  if (geometry.type === "Polygon") {
    const polygon = polygonOf(geometry.coordinates);
    return polygon ? [polygon] : [];
  }
  if (geometry.type === "MultiPolygon" && Array.isArray(geometry.coordinates)) {
    const polygons = geometry.coordinates.map(polygonOf);
    return polygons.every((p): p is PolygonRings => p !== null) ? polygons : [];
  }
  return [];
}

export function pointOf(geometry: MapFeatureView["geometry"]): LatLon | null {
  return geometry?.type === "Point" ? toLatLon(geometry.coordinates) : null;
}

export type LatLonBounds = [LatLon, LatLon];

/** Rectangle englobant [[sud, ouest], [nord, est]] ; null sans aucune position. */
export function boundsOf(positions: readonly LatLon[]): LatLonBounds | null {
  if (positions.length === 0) return null;
  let [south, west] = positions[0] as LatLon;
  let [north, east] = [south, west];
  for (const [lat, lon] of positions) {
    south = Math.min(south, lat);
    north = Math.max(north, lat);
    west = Math.min(west, lon);
    east = Math.max(east, lon);
  }
  return [
    [south, west],
    [north, east],
  ];
}

/** Centre du rectangle englobant de l'anneau extérieur : point d'ancrage des étiquettes. */
export function labelPoint(polygons: readonly PolygonRings[]): LatLon | null {
  const bounds = boundsOf(polygons.flatMap((p) => p[0] ?? []));
  if (!bounds) return null;
  const [[south, west], [north, east]] = bounds;
  return [(south + north) / 2, (west + east) / 2];
}

/* ---------- Fusion de la carte de base et de la couche demandée ---------- */

export interface MapFieldShape {
  props: FieldProps;
  polygons: PolygonRings[];
  /** Contour de la couche field_boundary ; null tant que la couche n'est pas demandée ou reçue. */
  boundary: PolygonRings[] | null;
}

export interface MapKitShape {
  props: DeviceProps;
  position: LatLon | null;
}

export interface FarmMapShapes {
  fields: MapFieldShape[];
  kits: MapKitShape[];
  bounds: LatLonBounds | null;
}

/**
 * Parcelles et kits d'une exploitation. La carte de base donne la géométrie, l'humidité et le NDVI ;
 * la couche (si reçue) ajoute culture détectée, salinité et contours. Une couche absente laisse ces valeurs à null :
 * jamais de valeur supposée.
 */
export function farmShapes(base: MapLayersView, overlay: MapLayersView | null): FarmMapShapes {
  const layerProps = new Map<string, FieldProps>();
  const boundaries = new Map<string, PolygonRings[]>();
  for (const feature of overlay?.features ?? []) {
    const p = feature.properties;
    if (p.kind === "field") layerProps.set(p.field_id, p);
    else if (p.kind === "boundary") boundaries.set(p.field_id, polygonsOf(feature.geometry));
  }
  const fields: MapFieldShape[] = [];
  const kits: MapKitShape[] = [];
  for (const feature of base.features) {
    const p = feature.properties;
    if (p.kind === "field") {
      const layer = layerProps.get(p.field_id);
      fields.push({
        props: { ...p, crop_type: layer?.crop_type ?? null, salinity_class: layer?.salinity_class ?? null },
        polygons: polygonsOf(feature.geometry),
        boundary: boundaries.get(p.field_id) ?? null,
      });
    } else if (p.kind === "device") {
      kits.push({ props: p, position: pointOf(feature.geometry) });
    }
  }
  const positions = [
    ...fields.flatMap((f) => f.polygons.flatMap((poly) => poly[0] ?? [])),
    ...kits.flatMap((k) => (k.position ? [k.position] : [])),
  ];
  return { fields, kits, bounds: boundsOf(positions) };
}

/* ---------- Modes de coloration ---------- */

export const MAP_MODES = ["moisture", "ndvi", "crop", "salinity"] as const;
export type MapMode = (typeof MAP_MODES)[number];

export const isMapMode = (value: string | null | undefined): value is MapMode =>
  (MAP_MODES as readonly string[]).includes(value ?? "");

/** Couche du service 18 que le mode exige ; humidité et NDVI viennent de la carte de base. */
export const MODE_LAYER: Readonly<Record<MapMode, MapLayer | null>> = {
  moisture: null,
  ndvi: null,
  crop: "crop_type",
  salinity: "salinity",
};

/** Couches à demander : celle du mode, plus les contours si l'option est cochée. Ordre stable (clé de cache). */
export function layersFor(mode: MapMode, withBoundaries: boolean): MapLayer[] {
  const layer = MODE_LAYER[mode];
  return [...(layer ? [layer] : []), ...(withBoundaries ? (["field_boundary"] as const) : [])];
}

/** Seuils NDVI des pas 2 à 5 (le pas 1 couvre tout ce qui est sous 0,2, valeurs négatives comprises). */
export const NDVI_STEPS = [0.2, 0.4, 0.6, 0.8] as const;

export function ndviStep(ndvi: number | null | undefined): RampStep {
  if (ndvi == null || !Number.isFinite(ndvi)) return 0;
  return (NDVI_STEPS.filter((threshold) => ndvi >= threshold).length + 1) as RampStep;
}

export const SALINITY_CLASSES: readonly SalinityClass[] = ["none", "low", "moderate", "high"];

const SALINITY_STEP: Readonly<Record<SalinityClass, RampStep>> = { none: 1, low: 2, moderate: 3, high: 4 };

export function salinityStep(value: SalinityClass | null | undefined): RampStep {
  return value ? SALINITY_STEP[value] : 0;
}

/** Pas de couleur d'une parcelle ; null en mode culture (remplissage neutre, la culture est écrite en clair). */
export function fillStep(mode: MapMode, props: FieldProps): RampStep | null {
  if (mode === "moisture") return moistureRamp(props.soil_moisture_pct);
  if (mode === "ndvi") return ndviStep(props.ndvi);
  if (mode === "salinity") return salinityStep(props.salinity_class);
  return null;
}

/** Classes écrites en entier, définies hors @layer dans globals.css (lib/ n'est pas lu par Tailwind). */
const FILL_CLASS: Readonly<Record<RampStep, string>> = {
  0: "map-fill-0",
  1: "map-fill-1",
  2: "map-fill-2",
  3: "map-fill-3",
  4: "map-fill-4",
  5: "map-fill-5",
};
export const NEUTRAL_FILL_CLASS = "map-fill-neutral";
export const SELECTED_CLASS = "map-selected";

export function fieldClass(mode: MapMode, props: FieldProps, selected: boolean): string {
  const step = fillStep(mode, props);
  const fill = step === null ? NEUTRAL_FILL_CLASS : FILL_CLASS[step];
  return selected ? `map-field ${fill} ${SELECTED_CLASS}` : `map-field ${fill}`;
}

/** Kit : actif, inactif ou retiré ; position estimée en pointillé (jamais présentée comme mesurée). */
export function kitClass(props: DeviceProps): string {
  const status = props.status === "active" ? "map-kit-active" : "map-kit-off";
  return props.position_estimated ? `map-kit ${status} map-kit-estimated` : `map-kit ${status}`;
}

/* ---------- Légende ---------- */

export type LegendItem =
  | { step: RampStep; kind: "noData" }
  /** from null : « moins de to » ; to null : « from et plus ». */
  | { step: RampStep; kind: "range"; from: number | null; to: number | null }
  | { step: RampStep; kind: "salinity"; value: SalinityClass };

const MOISTURE_STEP_PCT = 20;
const RAMP_STEPS: readonly RampStep[] = [1, 2, 3, 4, 5];

/** Légende du mode ; vide en mode culture (pas d'échelle de couleur : étiquettes permanentes). */
export function legendFor(mode: MapMode): LegendItem[] {
  const noData: LegendItem = { step: 0, kind: "noData" };
  if (mode === "moisture") {
    return [
      noData,
      ...RAMP_STEPS.map((step): LegendItem => ({
        step,
        kind: "range",
        from: (step - 1) * MOISTURE_STEP_PCT,
        to: step * MOISTURE_STEP_PCT,
      })),
    ];
  }
  if (mode === "ndvi") {
    return [
      noData,
      ...RAMP_STEPS.map((step, i): LegendItem => ({
        step,
        kind: "range",
        from: i === 0 ? null : (NDVI_STEPS[i - 1] ?? null),
        to: NDVI_STEPS[i] ?? null,
      })),
    ];
  }
  if (mode === "salinity") {
    return [noData, ...SALINITY_CLASSES.map((value): LegendItem => ({ step: SALINITY_STEP[value], kind: "salinity", value }))];
  }
  return [];
}

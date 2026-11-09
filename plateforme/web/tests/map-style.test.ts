/**
 * Carte (lib/map-style.ts, service 18 map_layers) : géométrie GeoJSON → Leaflet, fusion de la carte de base
 * et de la couche demandée, pas de couleur et légende. Les cartes viennent de la simulation de doc 16 §9.5.
 */
import { beforeEach, describe, expect, it } from "vitest";

import type { MapFeatureView, MapLayersView } from "@/lib/contracts/org";
import {
  MAP_MODES,
  NDVI_STEPS,
  NEUTRAL_FILL_CLASS,
  SELECTED_CLASS,
  boundsOf,
  farmShapes,
  fieldClass,
  fillStep,
  isMapMode,
  kitClass,
  labelPoint,
  layersFor,
  legendFor,
  ndviStep,
  pointOf,
  polygonsOf,
  salinityStep,
  toLatLon,
  type DeviceProps,
  type FieldProps,
} from "@/lib/map-style";
import { resetScenarios, resetStore } from "@/mocks";
import { fetchFarmMap } from "@/services/ai";

import { mockClient } from "./helpers";

process.env.AGRI_MOCK_LATENCY = "0";

beforeEach(() => {
  resetScenarios();
  resetStore();
});

const SQUARE = [
  [-16.9, 15.1],
  [-16.8, 15.1],
  [-16.8, 15.2],
  [-16.9, 15.2],
  [-16.9, 15.1],
];

const fieldProps = (overrides: Partial<FieldProps> = {}): FieldProps => ({
  kind: "field",
  field_id: "f1",
  name: "Parcelle",
  area_ha: 1,
  crop: "oignon",
  soil_moisture_pct: 45,
  open_alerts: 0,
  crop_type: null,
  salinity_class: null,
  ndvi: null,
  ...overrides,
});

const kitProps = (overrides: Partial<DeviceProps> = {}): DeviceProps => ({
  kind: "device",
  device_id: "d1",
  serial: "SA92-0001",
  field_id: "f1",
  status: "active",
  soil_moisture_pct: 45,
  measured_at: null,
  last_seen_at: null,
  open_alerts: 0,
  position_estimated: false,
  ...overrides,
});

describe("géométrie", () => {
  it("toLatLon inverse [lon, lat] et refuse les paires illisibles ou hors bornes", () => {
    expect(toLatLon([-16.9, 15.1])).toEqual([15.1, -16.9]);
    expect(toLatLon([-16.9, 15.1, 12])).toEqual([15.1, -16.9]);
    for (const bad of [null, [1], ["1", 2], [Number.NaN, 2], [181, 0], [0, 91]])
      expect(toLatLon(bad)).toBeNull();
  });

  it("polygonsOf : Polygon, MultiPolygon, et liste vide pour le reste", () => {
    expect(polygonsOf({ type: "Polygon", coordinates: [SQUARE] })).toHaveLength(1);
    expect(polygonsOf({ type: "MultiPolygon", coordinates: [[SQUARE], [SQUARE]] })).toHaveLength(2);
    expect(polygonsOf({ type: "Polygon", coordinates: [SQUARE] })[0]?.[0]?.[0]).toEqual([15.1, -16.9]);
    expect(polygonsOf(null)).toEqual([]);
    expect(polygonsOf({ type: "Point", coordinates: [-16.9, 15.1] })).toEqual([]);
    expect(polygonsOf({ type: "Polygon", coordinates: [] })).toEqual([]);
    expect(polygonsOf({ type: "Polygon", coordinates: [SQUARE.slice(0, 2)] })).toEqual([]);
    expect(polygonsOf({ type: "Polygon", coordinates: [[...SQUARE, [999, 0]]] })).toEqual([]);
    expect(polygonsOf({ type: "MultiPolygon", coordinates: [[SQUARE], []] })).toEqual([]);
    expect(polygonsOf({ type: "MultiPolygon", coordinates: "x" })).toEqual([]);
  });

  it("pointOf ne lit que les Point", () => {
    expect(pointOf({ type: "Point", coordinates: [-16.9, 15.1] })).toEqual([15.1, -16.9]);
    expect(pointOf({ type: "Polygon", coordinates: [SQUARE] })).toBeNull();
    expect(pointOf(null)).toBeNull();
  });

  it("boundsOf et labelPoint", () => {
    expect(boundsOf([])).toBeNull();
    expect(
      boundsOf([
        [15.2, -16.8],
        [15.1, -16.9],
      ]),
    ).toEqual([
      [15.1, -16.9],
      [15.2, -16.8],
    ]);
    const [lat, lon] = labelPoint(polygonsOf({ type: "Polygon", coordinates: [SQUARE] })) ?? [
      Number.NaN,
      Number.NaN,
    ];
    expect(lat).toBeCloseTo(15.15, 6);
    expect(lon).toBeCloseTo(-16.85, 6);
    expect(labelPoint([])).toBeNull();
  });
});

describe("farmShapes sur les cartes simulées", () => {
  const client = mockClient();

  it("sans couche reçue : culture et salinité à null, même si la base les porte", async () => {
    const base = await fetchFarmMap("farm-mboro", [], { client });
    expect(base.features.some((f) => f.properties.kind === "field" && f.properties.crop_type !== null)).toBe(
      true,
    );
    const shapes = farmShapes(base, null);
    expect(shapes.fields.length).toBeGreaterThan(0);
    expect(shapes.fields.every((f) => f.props.crop_type === null && f.props.salinity_class === null)).toBe(
      true,
    );
    expect(shapes.fields.every((f) => f.boundary === null && f.polygons.length === 1)).toBe(true);
    expect(shapes.kits.every((k) => k.position !== null && k.props.position_estimated)).toBe(true);
    expect(shapes.bounds).not.toBeNull();
  });

  it("avec la couche : culture, salinité et contours fusionnés par parcelle", async () => {
    const base = await fetchFarmMap("farm-mboro", ["crop_type"], { client });
    const overlay = await fetchFarmMap("farm-mboro", ["crop_type", "salinity", "field_boundary"], { client });
    const shapes = farmShapes(base, overlay);
    for (const f of shapes.fields) {
      expect(f.props.crop_type?.label).toBeTruthy();
      expect(f.props.salinity_class).not.toBeNull();
      expect(f.boundary?.length).toBeGreaterThan(0);
    }
  });

  it("une parcelle sans géométrie reste listée, sans polygone ni influence sur l'emprise", () => {
    const feature: MapFeatureView = { type: "Feature", id: "f1", geometry: null, properties: fieldProps() };
    const base: MapLayersView = {
      type: "FeatureCollection",
      features: [feature],
      layers: {},
      provenance: null,
    };
    expect(farmShapes(base, null)).toEqual({
      fields: [{ props: fieldProps(), polygons: [], boundary: null }],
      kits: [],
      bounds: null,
    });
  });
});

describe("modes et pas de couleur", () => {
  it("modes connus et couches à demander dans un ordre stable", () => {
    expect(MAP_MODES).toEqual(["moisture", "ndvi", "crop", "salinity"]);
    expect(isMapMode("ndvi")).toBe(true);
    expect(isMapMode("relief")).toBe(false);
    expect(isMapMode(null)).toBe(false);
    expect(layersFor("moisture", false)).toEqual([]);
    expect(layersFor("crop", true)).toEqual(["crop_type", "field_boundary"]);
    expect(layersFor("salinity", false)).toEqual(["salinity"]);
    expect(layersFor("ndvi", true)).toEqual(["field_boundary"]);
  });

  it.each([
    [null, 0],
    [Number.NaN, 0],
    [-0.3, 1],
    [0.19, 1],
    [0.2, 2],
    [0.4, 3],
    [0.6, 4],
    [0.79, 4],
    [0.8, 5],
    [1, 5],
  ])("ndviStep(%s) = %i", (ndvi, step) => {
    expect(NDVI_STEPS).toEqual([0.2, 0.4, 0.6, 0.8]);
    expect(ndviStep(ndvi)).toBe(step);
  });

  it("salinityStep et fillStep par mode ; null en mode culture", () => {
    expect([salinityStep(null), salinityStep("none"), salinityStep("high")]).toEqual([0, 1, 4]);
    const props = fieldProps({ soil_moisture_pct: 85, ndvi: 0.45, salinity_class: "moderate" });
    expect([
      fillStep("moisture", props),
      fillStep("ndvi", props),
      fillStep("salinity", props),
      fillStep("crop", props),
    ]).toEqual([5, 3, 3, null]);
  });

  it("classes CSS : remplissage par pas, neutre en mode culture, sélection", () => {
    expect(fieldClass("moisture", fieldProps({ soil_moisture_pct: null }), false)).toBe(
      "map-field map-fill-0",
    );
    expect(fieldClass("crop", fieldProps(), true)).toBe(`map-field ${NEUTRAL_FILL_CLASS} ${SELECTED_CLASS}`);
    expect(kitClass(kitProps())).toBe("map-kit map-kit-active");
    expect(kitClass(kitProps({ status: "retired", position_estimated: true }))).toBe(
      "map-kit map-kit-off map-kit-estimated",
    );
  });
});

describe("legendFor", () => {
  it("humidité : pas de mesure, puis cinq tranches de 20 %", () => {
    const legend = legendFor("moisture");
    expect(legend[0]).toEqual({ step: 0, kind: "noData" });
    expect(legend.slice(1)).toEqual(
      [0, 20, 40, 60, 80].map((from, i) => ({ step: i + 1, kind: "range", from, to: from + 20 })),
    );
  });

  it("NDVI : bornes ouvertes aux extrémités", () => {
    const legend = legendFor("ndvi");
    expect(legend[1]).toEqual({ step: 1, kind: "range", from: null, to: 0.2 });
    expect(legend[5]).toEqual({ step: 5, kind: "range", from: 0.8, to: null });
  });

  it("salinité : quatre classes ; culture : aucune échelle", () => {
    expect(legendFor("salinity").map((item) => item.step)).toEqual([0, 1, 2, 3, 4]);
    expect(legendFor("crop")).toEqual([]);
  });
});

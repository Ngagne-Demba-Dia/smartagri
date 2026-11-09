/**
 * Référentiel de démonstration : deux organisations fictives, trois périmètres maraîchers (Niayes, vallée
 * du fleuve), sept parcelles, cinq kits. Noms explicitement « démo » : aucune organisation ni personne réelle.
 * Les dates relatives (campagnes, cycles) sont calculées à partir de `now` à chaque requête.
 */
import type { Campaign, CropCycle, Device, Equipment, Farm, Field, GeoJsonPolygon, IrrigationType } from "@/lib/types";

import { DAY_MS, HOUR_MS, iso, isoDay } from "../base";

export const ORG_A = "org-demo-niayes";
export const ORG_A_NAME = "Coopérative démo — Niayes";
export const ORG_B = "org-demo-ndiol";
export const ORG_B_NAME = "Exploitation démo — Ndiol";

const CREATED_AT = "2026-09-01T08:00:00Z";
const M_PER_DEG_LAT = 111_000;
const M2_PER_HA = 10_000;
export const DEFAULT_THRESHOLDS = { start_pct: 30, stop_pct: 60 } as const;
export const FIRMWARE_VERSION = "1.1.0";

export const FARMS: readonly Farm[] = [
  farm("farm-mboro", ORG_A, "Périmètre de Mboro", "Thiès", "Mboro", 15.14, -16.88, 1.7),
  farm("farm-potou", ORG_A, "Périmètre de Potou", "Louga", "Potou", 15.72, -16.48, 2.1),
  farm("farm-ndiol", ORG_B, "Périmètre de Ndiol", "Saint-Louis", "Ross-Béthio", 16.18, -16.32, 1.6),
];

function farm(id: string, org: string, name: string, region: string, commune: string, lat: number, lon: number, ha: number): Farm {
  return { id, organization_id: org, name, region, commune, latitude: lat, longitude: lon, area_ha: ha, created_at: CREATED_AT };
}

/** Graine d'une parcelle : la culture active et son calendrier pilotent NDVI, rendement et recommandations. */
export interface FieldSeed {
  id: string;
  farmId: string;
  orgId: string;
  name: string;
  areaHa: number;
  soil: string;
  irrigation: IrrigationType;
  lat: number;
  lon: number;
  /** null : aucun cycle actif (yield_forecast répond 404 NO_ACTIVE_CYCLE). */
  crop: string | null;
  variety: string | null;
  plantedDaysAgo: number;
  cycleDays: number;
  deviceId: string | null;
  pumpId: string;
}

const DIOR = "sableux (dior)";
const DECK = "sablo-argileux (deck)";
const HOLLALDE = "argileux (hollaldé)";

export const FIELD_SEEDS: readonly FieldSeed[] = [
  seed("fld-mboro-1", "farm-mboro", ORG_A, "Mboro 1", 0.5, DIOR, "drip", 15.141, -16.881, "oignon", "Violet de Galmi", 45, 120, "dev-0001", "eq-mboro-pump"),
  seed("fld-mboro-2", "farm-mboro", ORG_A, "Mboro 2", 0.8, DECK, "drip", 15.141, -16.879, "tomate", null, 60, 110, "dev-0002", "eq-mboro-pump"),
  seed("fld-mboro-3", "farm-mboro", ORG_A, "Mboro 3", 0.4, DIOR, "sprinkler", 15.139, -16.88, "chou", null, 30, 90, null, "eq-mboro-pump"),
  seed("fld-potou-1", "farm-potou", ORG_A, "Potou 1", 1.2, DIOR, "furrow", 15.7205, -16.4805, "carotte", "Nantaise", 50, 100, "dev-0003", "eq-potou-pump"),
  seed("fld-potou-2", "farm-potou", ORG_A, "Potou 2", 0.9, DECK, "drip", 15.7185, -16.479, "pomme de terre", null, 40, 95, "dev-0004", "eq-potou-pump"),
  seed("fld-ndiol-1", "farm-ndiol", ORG_B, "Ndiol 1", 1.0, HOLLALDE, "drip", 16.1805, -16.3205, "oignon", "Violet de Galmi", 35, 120, "dev-0101", "eq-ndiol-pump"),
  seed("fld-ndiol-2", "farm-ndiol", ORG_B, "Ndiol 2", 0.6, HOLLALDE, "manual", 16.179, -16.3185, null, null, 0, 0, null, "eq-ndiol-pump"),
];

function seed(
  id: string, farmId: string, orgId: string, name: string, areaHa: number, soil: string, irrigation: IrrigationType,
  lat: number, lon: number, crop: string | null, variety: string | null, plantedDaysAgo: number, cycleDays: number,
  deviceId: string | null, pumpId: string,
): FieldSeed {
  return { id, farmId, orgId, name, areaHa, soil, irrigation, lat, lon, crop, variety, plantedDaysAgo, cycleDays, deviceId, pumpId };
}

const round6 = (value: number) => Math.round(value * 1e6) / 1e6;

/** Carré de la surface de la parcelle centré sur son centroïde (côté = √(ha × 10 000) m). */
export function rectangle(lat: number, lon: number, areaHa: number): GeoJsonPolygon {
  const halfSide = Math.sqrt(areaHa * M2_PER_HA) / 2;
  const dLat = halfSide / M_PER_DEG_LAT;
  const dLon = dLat / Math.cos((lat * Math.PI) / 180);
  const corners: Array<[number, number]> = [
    [lon - dLon, lat - dLat],
    [lon + dLon, lat - dLat],
    [lon + dLon, lat + dLat],
    [lon - dLon, lat + dLat],
    [lon - dLon, lat - dLat],
  ];
  return { type: "Polygon", coordinates: [corners.map(([x, y]) => [round6(x), round6(y)])] };
}

export function toField(s: FieldSeed): Field {
  return {
    id: s.id,
    organization_id: s.orgId,
    farm_id: s.farmId,
    name: s.name,
    area_ha: s.areaHa,
    soil_type: s.soil,
    irrigation_type: s.irrigation,
    geometry: rectangle(s.lat, s.lon, s.areaHa),
    centroid: { longitude: s.lon, latitude: s.lat },
    created_at: CREATED_AT,
  };
}

/** Graine d'un kit : NPK de base (mg/kg) et décalage de phase du cycle d'humidité. */
export interface DeviceSeed {
  id: string;
  serial: string;
  orgId: string;
  fieldId: string;
  status: Device["status"];
  /** Dernier contact, en heures avant maintenant (0 : en ligne). */
  silentHours: number;
  npk: { n: number; p: number; k: number };
}

export const DEVICE_SEEDS: readonly DeviceSeed[] = [
  { id: "dev-0001", serial: "SA92-0001", orgId: ORG_A, fieldId: "fld-mboro-1", status: "active", silentHours: 0, npk: { n: 62, p: 28, k: 115 } },
  { id: "dev-0002", serial: "SA92-0002", orgId: ORG_A, fieldId: "fld-mboro-2", status: "active", silentHours: 0, npk: { n: 48, p: 22, k: 96 } },
  { id: "dev-0003", serial: "SA92-0003", orgId: ORG_A, fieldId: "fld-potou-1", status: "active", silentHours: 0, npk: { n: 35, p: 14, k: 70 } },
  { id: "dev-0004", serial: "SA92-0004", orgId: ORG_A, fieldId: "fld-potou-2", status: "inactive", silentHours: 72, npk: { n: 55, p: 25, k: 104 } },
  { id: "dev-0101", serial: "SA92-0101", orgId: ORG_B, fieldId: "fld-ndiol-1", status: "active", silentHours: 0, npk: { n: 70, p: 31, k: 128 } },
];

export function lastSeen(d: DeviceSeed, now: Date): Date {
  const minutes = d.silentHours === 0 ? 4 : d.silentHours * 60;
  return new Date(now.getTime() - minutes * 60_000);
}

export const farmById = (id: string) => FARMS.find((f) => f.id === id) ?? null;
export const fieldSeedById = (id: string) => FIELD_SEEDS.find((f) => f.id === id) ?? null;
export const deviceSeedById = (id: string) => DEVICE_SEEDS.find((d) => d.id === id) ?? null;
export const fieldSeedsOfFarm = (farmId: string) => FIELD_SEEDS.filter((f) => f.farmId === farmId);
export const deviceSeedOfField = (fieldId: string) => DEVICE_SEEDS.find((d) => d.fieldId === fieldId) ?? null;

/* ---------- Campagnes, cycles, équipements ---------- */

export const ACTIVE_CAMPAIGN_ID = "cmp-contre-saison";

export function campaigns(now: Date): Campaign[] {
  const at = (days: number) => isoDay(new Date(now.getTime() + days * DAY_MS));
  return [
    { id: ACTIVE_CAMPAIGN_ID, organization_id: ORG_A, name: "Contre-saison froide", season: "dry", start_date: at(-60), end_date: at(90), status: "active", created_at: CREATED_AT },
    { id: "cmp-hivernage", organization_id: ORG_A, name: "Hivernage", season: "rainy", start_date: at(-200), end_date: at(-75), status: "closed", created_at: CREATED_AT },
    { id: "cmp-ndiol-cs", organization_id: ORG_B, name: "Contre-saison froide", season: "dry", start_date: at(-50), end_date: at(100), status: "active", created_at: CREATED_AT },
  ];
}

export function plantedOn(s: FieldSeed, now: Date): string {
  return isoDay(new Date(now.getTime() - s.plantedDaysAgo * DAY_MS));
}

export function activeCycle(s: FieldSeed, now: Date): CropCycle | null {
  if (!s.crop) return null;
  const planted = new Date(now.getTime() - s.plantedDaysAgo * DAY_MS);
  return {
    id: `cyc-${s.id}`,
    organization_id: s.orgId,
    field_id: s.id,
    campaign_id: s.orgId === ORG_A ? ACTIVE_CAMPAIGN_ID : "cmp-ndiol-cs",
    crop: s.crop,
    variety: s.variety,
    planted_on: isoDay(planted),
    expected_harvest_on: isoDay(new Date(planted.getTime() + s.cycleDays * DAY_MS)),
    harvested_on: null,
    yield_kg: null,
    status: "active",
    created_at: iso(planted),
  };
}

/** Cycle récolté de l'hivernage précédent (rendement réel connu). */
function harvestedCycle(s: FieldSeed, now: Date, crop: string, tHa: number): CropCycle {
  const planted = new Date(now.getTime() - 200 * DAY_MS);
  return {
    id: `cyc-${s.id}-prev`,
    organization_id: s.orgId,
    field_id: s.id,
    campaign_id: s.orgId === ORG_A ? "cmp-hivernage" : null,
    crop,
    variety: null,
    planted_on: isoDay(planted),
    expected_harvest_on: isoDay(new Date(planted.getTime() + 110 * DAY_MS)),
    harvested_on: isoDay(new Date(planted.getTime() + 115 * DAY_MS)),
    yield_kg: Math.round(tHa * s.areaHa * 1000),
    status: "harvested",
    created_at: iso(planted),
  };
}

export function cropCycles(s: FieldSeed, now: Date): CropCycle[] {
  const active = activeCycle(s, now);
  const previous = s.id === "fld-ndiol-2" ? harvestedCycle(s, now, "riz", 5.5) : s.id === "fld-mboro-1" ? harvestedCycle(s, now, "oignon", 21) : null;
  return [active, previous].filter((c): c is CropCycle => c !== null);
}

export const EQUIPMENT: readonly Equipment[] = [
  equipment("eq-mboro-pump", ORG_A, "farm-mboro", "pump", "Pompe solaire Mboro", "PMP-DEMO-01", "ok", "dev-0001", 2.5),
  equipment("eq-mboro-tank", ORG_A, "farm-mboro", "tank", "Réservoir 10 m³", null, "ok", null, null),
  equipment("eq-mboro-solar", ORG_A, "farm-mboro", "solar_panel", "Champ solaire 1,2 kWc", "PV-DEMO-01", "ok", null, null),
  equipment("eq-potou-pump", ORG_A, "farm-potou", "pump", "Pompe solaire Potou", "PMP-DEMO-02", "ok", "dev-0003", 3),
  equipment("eq-potou-tank", ORG_A, "farm-potou", "tank", "Bassin 20 m³", null, "ok", null, null),
  equipment("eq-potou-solar", ORG_A, "farm-potou", "solar_panel", "Champ solaire 1,5 kWc", "PV-DEMO-02", "maintenance", null, null),
  equipment("eq-ndiol-pump", ORG_B, "farm-ndiol", "pump", "Pompe solaire Ndiol", "PMP-DEMO-03", "maintenance", "dev-0101", 2),
  equipment("eq-ndiol-solar", ORG_B, "farm-ndiol", "solar_panel", "Champ solaire 1 kWc", "PV-DEMO-03", "ok", null, null),
];

function equipment(
  id: string, org: string, farmId: string, kind: Equipment["kind"], label: string, serial: string | null,
  status: Equipment["status"], deviceId: string | null, flow: number | null,
): Equipment {
  return {
    id, organization_id: org, farm_id: farmId, kind, label, serial, installed_at: "2026-02-15", status,
    device_id: deviceId, flow_m3h: flow, created_at: CREATED_AT,
  };
}

export const pumpFlow = (pumpId: string): number => EQUIPMENT.find((e) => e.id === pumpId)?.flow_m3h ?? 2;

/* ---------- Alertes de départ ---------- */

export interface AlertSeed {
  id: string;
  deviceId: string;
  rule: string;
  severity: "info" | "warning" | "critical";
  status: "open" | "acknowledged" | "resolved";
  message: string;
  hoursAgo: number;
  details: Record<string, unknown> | null;
}

export const ALERT_SEEDS: readonly AlertSeed[] = [
  { id: "alt-0001", deviceId: "dev-0002", rule: "soil_dry", severity: "warning", status: "open", hoursAgo: 3, message: "Humidité du sol sous le seuil de démarrage (24 %).", details: { soil_moisture_pct: 24, threshold_start_pct: 30 } },
  { id: "alt-0002", deviceId: "dev-0004", rule: "device_offline", severity: "critical", status: "open", hoursAgo: 48, message: "Kit sans nouvelles depuis plus de 24 h.", details: null },
  { id: "alt-0003", deviceId: "dev-0003", rule: "fertilizer_low", severity: "info", status: "open", hoursAgo: 20, message: "Potassium indicatif bas : à confirmer par une analyse de sol.", details: { k_mgkg: 70 } },
  { id: "alt-0004", deviceId: "dev-0001", rule: "sensor_fault", severity: "warning", status: "acknowledged", hoursAgo: 26, message: "Capteur air (BME280) sans réponse pendant 10 min.", details: { sensor: "bme" } },
  { id: "alt-0005", deviceId: "dev-0101", rule: "pump_fault", severity: "critical", status: "open", hoursAgo: 5, message: "Pompe commandée sans débit mesuré.", details: { pump_on: true, flow_m3h: 0 } },
  { id: "alt-0006", deviceId: "dev-0002", rule: "soil_dry", severity: "warning", status: "resolved", hoursAgo: 72, message: "Humidité du sol sous le seuil de démarrage (27 %).", details: { soil_moisture_pct: 27, threshold_start_pct: 30 } },
];

export const hoursBefore = (now: Date, hours: number): Date => new Date(now.getTime() - hours * HOUR_MS);

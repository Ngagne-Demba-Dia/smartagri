/**
 * Réponses simulées à l'échelle de l'exploitation ou de l'organisation : référentiel, plan d'irrigation,
 * rapport KPI (dont water_savings), prix et couches de carte (doc 16 §9, services 4, 14, 15 et 18).
 */
import type { IrrigationPlan, KpiReportView, MapFeatureView, MapLayer, MapLayersView, PriceForecast, WaterSavings } from "@/lib/contracts/org";
import type { Campaign, Equipment, Farm, Field } from "@/lib/types";

import type { Principal } from "../auth";
import { DAY_MS, HOUR_MS, addDays, iso, isoDay, round } from "../base";
import {
  ALERT_SEEDS,
  EQUIPMENT,
  ORG_B,
  campaigns,
  deviceSeedOfField,
  fieldSeedsOfFarm,
  lastSeen,
  pumpFlow,
  rectangle,
  toField,
  type DeviceSeed,
  type FieldSeed,
} from "../fixtures/places";
import { between, hash32 } from "../fixtures/series";
import { MAP_LAYER_MODELS, NO_CONFIDENCE, classProbability, interval, provenance } from "../provenance";
import type { MockScenario } from "../scenario";
import { diagnosisCounts, feedbackCounts } from "../store";

import { kitReading } from "./common";
import { flowMissing, openAlertCount } from "./device";
import { latestNdvi, plannedVolume } from "./field";

export const campaignsView = (user: Principal, now: Date): Campaign[] => campaigns(now).filter((c) => user.orgIds.has(c.organization_id));
export const equipmentView = (user: Principal): Equipment[] => EQUIPMENT.filter((e) => user.orgIds.has(e.organization_id));
export const farmFields = (farm: Farm): Field[] => fieldSeedsOfFarm(farm.id).map(toField);

/* ---------- 4. irrigation_plan ---------- */

const PLAN_START_HOUR_UTC = 6;

export function irrigationPlan(farm: Farm, date: Date, scenario: MockScenario, now: Date): IrrigationPlan {
  const day = isoDay(date);
  const cursor = new Map<string, number>();
  const slots: IrrigationPlan["slots"] = [];
  if (scenario !== "empty") {
    for (const seed of fieldSeedsOfFarm(farm.id)) {
      const volume = plannedVolume(seed, scenario, now);
      if (volume <= 0) continue;
      const start = cursor.get(seed.pumpId) ?? new Date(`${day}T0${PLAN_START_HOUR_UTC}:00:00Z`).getTime();
      const end = start + Math.round((volume / pumpFlow(seed.pumpId)) * HOUR_MS);
      cursor.set(seed.pumpId, end);
      slots.push({ field_id: seed.id, pump_id: seed.pumpId, start: iso(new Date(start)), end: iso(new Date(end)), volume_m3: volume });
    }
  }
  const total = slots.reduce((acc, s) => acc + s.volume_m3, 0);
  return {
    farm_id: farm.id,
    date: day,
    slots,
    provenance: provenance("irrigation_plan", scenario, now, {
      confidence: total > 0 ? interval(round(total * 0.85, 1), round(total * 1.15, 1), false) : NO_CONFIDENCE,
    }),
  };
}

/* ---------- 14. water_savings dans le rapport KPI ---------- */

export interface KpiScope {
  scope: KpiReportView["scope"];
  scopeId: string;
  fields: readonly FieldSeed[];
}

const UPTIME_ONLINE_PCT = 99.2;
const MEASUREMENTS_PER_DAY = 288;
const IRRIGATION_EVENTS_PER_MONTH = 24;
const SAVED_SHARE = 0.18;
const BASE_DIAGNOSES = { healthy: 12, suspect: 4, sick: 3 } as const;
const SAVINGS_METHOD = "comparaison avec parcelles témoins (irrigation au calendrier)";

const daysBetween = (from: Date, to: Date) => Math.max(1, Math.round((to.getTime() - from.getTime()) / DAY_MS));

function waterUse(fields: readonly FieldSeed[], days: number): number {
  return fields.reduce((acc, f) => acc + between(`${f.id}:water`, 3, 6) * f.areaHa * 10 * days, 0);
}

function uptime(devices: readonly DeviceSeed[], days: number): number | null {
  if (devices.length === 0) return null;
  const hours = days * 24;
  const values = devices.map((d) => (d.status === "active" ? UPTIME_ONLINE_PCT : Math.max(0, (1 - d.silentHours / hours) * 100)));
  return round(values.reduce((a, b) => a + b, 0) / values.length, 1);
}

function waterSavings(water: number, scenario: MockScenario, now: Date): WaterSavings | null {
  if (scenario === "error_503" || scenario === "empty") return null;
  const saved = round(water * SAVED_SHARE, 0);
  const pct = round((saved / (water + saved)) * 100, 1);
  return {
    saved_m3: saved,
    saved_pct: pct,
    method: SAVINGS_METHOD,
    control_fields: 2,
    provenance: provenance("water_savings", scenario, now, { confidence: interval(round(saved * 0.7, 0), round(saved * 1.3, 0), false) }),
  };
}

export function kpiReport(scope: KpiScope, from: Date, to: Date, scenario: MockScenario, now: Date): KpiReportView {
  const days = daysBetween(from, to);
  const devices = scope.fields.flatMap((f) => {
    const d = deviceSeedOfField(f.id);
    return d ? [d] : [];
  });
  const water = round(waterUse(scope.fields, days), 0);
  const deviceIds = new Set(devices.map((d) => d.id));
  const alertsByRule: Record<string, number> = {};
  for (const a of ALERT_SEEDS) if (deviceIds.has(a.deviceId)) alertsByRule[a.rule] = (alertsByRule[a.rule] ?? 0) + 1;
  const stored = diagnosisCounts();
  const feedback = feedbackCounts();
  const feedbackTotal = Object.values(feedback).reduce((a, b) => a + b, 0);
  const meanFlow = scope.fields.length ? scope.fields.reduce((a, f) => a + pumpFlow(f.pumpId), 0) / scope.fields.length : 2;
  return {
    scope: scope.scope,
    scope_id: scope.scopeId,
    from: isoDay(from),
    to: isoDay(to),
    kpis: {
      devices: devices.length,
      fields: scope.fields.length,
      water_m3: water,
      devices_without_flow: devices.filter((d) => flowMissing(d, now)).length,
      pump_hours: round(water / meanFlow, 1),
      irrigation_events: Math.round((days * IRRIGATION_EVENTS_PER_MONTH * devices.length) / 30),
      measurements: devices.length * days * MEASUREMENTS_PER_DAY,
      kit_uptime_pct: uptime(devices, days),
      alerts_by_rule: alertsByRule,
      diagnoses_by_label: {
        healthy: BASE_DIAGNOSES.healthy + stored.healthy,
        suspect: BASE_DIAGNOSES.suspect + stored.suspect,
        sick: BASE_DIAGNOSES.sick + stored.sick,
      },
      recommendations_feedback: { ...feedback },
      recommendations_followed_pct: feedbackTotal > 0 ? round((feedback.followed / feedbackTotal) * 100, 1) : null,
      water_savings: waterSavings(water, scenario, now),
    },
  };
}

const csvCell = (value: string | number | null): string => {
  const text = value === null ? "" : String(value);
  return /[";,\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

/** Export CSV du rapport (une ligne par parcelle, séparateur « ; » pour les tableurs français). */
export function kpiCsv(scope: KpiScope, from: Date, to: Date): string {
  const days = daysBetween(from, to);
  const header = ["field_id", "nom", "surface_ha", "culture", "kit", "eau_m3", "from", "to"];
  const rows = scope.fields.map((f) => [
    f.id,
    f.name,
    f.areaHa,
    f.crop,
    deviceSeedOfField(f.id)?.serial ?? null,
    round(waterUse([f], days), 0),
    isoDay(from),
    isoDay(to),
  ]);
  return [header, ...rows].map((row) => row.map(csvCell).join(";")).join("\n") + "\n";
}

/* ---------- 15. price_forecast ---------- */

const BASE_PRICE_XOF_KG: Readonly<Record<string, number>> = { oignon: 350, tomate: 300, chou: 200, carotte: 400, "pomme de terre": 375 };
export const PRICE_CROPS = Object.keys(BASE_PRICE_XOF_KG);
const OBSERVED_AGO_DAYS = 2;

/** null : culture inconnue (404). */
export function priceForecast(crop: string, market: string, scenario: MockScenario, now: Date): PriceForecast | null {
  const base = BASE_PRICE_XOF_KG[crop];
  if (base === undefined) return null;
  const marketFactor = 0.9 + (hash32(market.toLowerCase()) % 21) / 100;
  const observed = Math.round(base * marketFactor);
  const trend = between(`${crop}:${market}:${isoDay(now)}`, -0.03, 0.04);
  const horizons =
    scenario === "empty" || scenario === "abstention"
      ? []
      : [1, 2, 3, 4].map((weeks) => {
          const p50 = Math.round(observed * (1 + trend * weeks));
          return { weeks, p10: Math.round(p50 * (1 - 0.06 * weeks)), p50, p90: Math.round(p50 * (1 + 0.07 * weeks)) };
        });
  const first = horizons[0];
  const observedOn = addDays(now, -OBSERVED_AGO_DAYS);
  return {
    crop,
    market,
    currency: "XOF",
    unit: "kg",
    observed: scenario === "empty" ? null : { date: isoDay(observedOn), price: observed },
    horizons,
    provenance: provenance("price_forecast", scenario, now, {
      confidence: first ? interval(first.p10, first.p90, true) : NO_CONFIDENCE,
      dataAsOf: observedOn,
    }),
  };
}

/* ---------- 18. map_layers ---------- */

type SalinityClass = "none" | "low" | "moderate" | "high";
const SALINITY: readonly SalinityClass[] = ["none", "low", "moderate", "high"];

function salinityOf(seed: FieldSeed): SalinityClass {
  const offset = seed.orgId === ORG_B ? 2 : 0;
  return SALINITY[Math.min(3, offset + (hash32(`${seed.id}:sal`) % 2))] ?? "none";
}

function fieldFeature(seed: FieldSeed, layers: ReadonlySet<MapLayer>, scenario: MockScenario, now: Date): MapFeatureView {
  const device = deviceSeedOfField(seed.id);
  const field = toField(seed);
  const p = round(between(`${seed.id}:crop_type`, 0.72, 0.95), 2);
  return {
    type: "Feature",
    id: seed.id,
    geometry: field.geometry,
    properties: {
      kind: "field",
      field_id: seed.id,
      name: seed.name,
      area_ha: seed.areaHa,
      crop: seed.crop,
      soil_moisture_pct: kitReading(seed, now)?.moisture ?? null,
      open_alerts: device ? openAlertCount(device.id) : 0,
      crop_type: layers.has("crop_type") ? { label: seed.crop ?? "sol nu", probability: scenario === "abstention" ? null : p } : null,
      salinity_class: layers.has("salinity") ? salinityOf(seed) : null,
      ndvi: latestNdvi(seed, now),
    },
  };
}

function deviceFeature(seed: FieldSeed, device: DeviceSeed, now: Date): MapFeatureView {
  const reading = kitReading(seed, now);
  return {
    type: "Feature",
    id: device.id,
    geometry: { type: "Point", coordinates: [round(seed.lon + 0.0004, 5), round(seed.lat - 0.0003, 5)] },
    properties: {
      kind: "device",
      device_id: device.id,
      serial: device.serial,
      field_id: seed.id,
      status: device.status,
      soil_moisture_pct: reading?.moisture ?? null,
      measured_at: reading ? iso(reading.measuredAt) : null,
      last_seen_at: iso(lastSeen(device, now)),
      open_alerts: openAlertCount(device.id),
      position_estimated: true,
    },
  };
}

const boundaryFeature = (seed: FieldSeed): MapFeatureView => ({
  type: "Feature",
  id: `bnd-${seed.id}`,
  geometry: rectangle(seed.lat, seed.lon, seed.areaHa * 1.02),
  properties: { kind: "boundary", field_id: seed.id, area_ha: round(seed.areaHa * 1.02, 2) },
});

export function mapLayers(farm: Farm, layers: ReadonlySet<MapLayer>, scenario: MockScenario, now: Date): MapLayersView {
  if (scenario === "empty") return { type: "FeatureCollection", features: [], layers: {}, provenance: null };
  const seeds = fieldSeedsOfFarm(farm.id);
  const features = seeds.flatMap((seed) => {
    const device = deviceSeedOfField(seed.id);
    const out = [fieldFeature(seed, layers, scenario, now)];
    if (device) out.push(deviceFeature(seed, device, now));
    if (layers.has("field_boundary")) out.push(boundaryFeature(seed));
    return out;
  });
  const cropProbs = seeds.map((s) => round(between(`${s.id}:crop_type`, 0.72, 0.95), 2));
  const meanCrop = cropProbs.length ? round(cropProbs.reduce((a, b) => a + b, 0) / cropProbs.length, 2) : null;
  const perLayer: Record<string, MapLayersView["layers"][string]> = {};
  for (const layer of layers) {
    perLayer[layer] = provenance("map_layers", scenario, now, {
      model: MAP_LAYER_MODELS[layer],
      confidence: layer === "crop_type" ? classProbability(meanCrop, true) : NO_CONFIDENCE,
      dataAsOf: addDays(now, -3),
    });
  }
  return {
    type: "FeatureCollection",
    features,
    layers: perLayer,
    provenance: layers.size > 0 ? provenance("map_layers", scenario, now, { dataAsOf: addDays(now, -3) }) : null,
  };
}

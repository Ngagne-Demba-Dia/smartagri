/**
 * Réponses simulées des services rattachés à une parcelle (doc 16 §9) : météo, sol, besoin en eau,
 * recommandations, fertilisation, ravageurs, végétation, rendement. Fonctions pures de (graine, scénario, now).
 */
import type {
  Fertilization,
  IrrigationNeed,
  PestRisk,
  RecommendationView,
  SoilForecast,
  Vegetation,
  WeatherForecastView,
  YieldForecast,
} from "@/lib/contracts/field";
import type { CropCycle, FieldDetail } from "@/lib/types";

import { DAY_MS, HOUR_MS, floorHour, iso, isoDay, round } from "../base";
import { DEFAULT_THRESHOLDS, activeCycle, cropCycles, deviceSeedOfField, lastSeen, toField, type FieldSeed } from "../fixtures/places";
import { bbchStage, between, ndviSeries, npkAt, soilAt, weatherDays } from "../fixtures/series";
import { NO_CONFIDENCE, interval, nominalModel, probability, provenance } from "../provenance";
import type { MockScenario } from "../scenario";
import { effectiveThresholds } from "../store";

import { IRRIGATION_EFFICIENCY, clamp, cropKc, kitReading, mmToM3, pestsOf, plantedDate } from "./common";

export const fieldDetail = (seed: FieldSeed, now: Date): FieldDetail => ({ ...toField(seed), active_cycle: activeCycle(seed, now) });
export const cropCyclesView = (seed: FieldSeed, now: Date): CropCycle[] => cropCycles(seed, now);

const degraded = (scenario: MockScenario) => scenario === "fallback" || scenario === "abstention";

/* ---------- 1. weather ---------- */

const STALE_WEATHER_MS = 6 * HOUR_MS;
const FRESH_WEATHER_MS = 20 * 60_000;

export function weather(seed: FieldSeed, days: number, scenario: MockScenario, now: Date): WeatherForecastView {
  const samples = scenario === "empty" ? [] : weatherDays(seed.id, now, days);
  const dropModel = degraded(scenario);
  const rows = samples.map((d) => ({
    ...d,
    rain_probability: dropModel ? null : d.rain_probability,
    rain_threshold_mm: scenario === "abstention" ? null : d.rain_threshold_mm,
    local_bias_c: dropModel ? null : d.local_bias_c,
  }));
  const headline = samples[1]?.rain_probability ?? samples[0]?.rain_probability ?? null;
  const fetchedAt = new Date(now.getTime() - (scenario === "stale" ? STALE_WEATHER_MS : FRESH_WEATHER_MS));
  return {
    field_id: seed.id,
    location_source: "field_centroid",
    provider: "open-meteo",
    latitude: seed.lat,
    longitude: seed.lon,
    fetched_at: iso(fetchedAt),
    source: scenario === "stale" ? "stale_cache" : "provider",
    days: rows,
    provenance: provenance("weather", scenario, now, {
      confidence: headline === null ? NO_CONFIDENCE : probability(headline, true),
      dataAsOf: fetchedAt,
    }),
  };
}

/* ---------- 2. soil_forecast ---------- */

export const DEFAULT_SOIL_HORIZONS = [24, 48, 72] as const;

export function soilForecast(seed: FieldSeed, horizons: readonly number[], scenario: MockScenario, now: Date): SoilForecast {
  const device = deviceSeedOfField(seed.id);
  const issued = floorHour(now);
  if (!device) {
    return { field_id: seed.id, device_id: null, issued_at: iso(issued), horizons: [], thresholds: null, provenance: provenance("soil_forecast", scenario, now, { dataAsOf: null }) };
  }
  const thresholds = effectiveThresholds(device.id, now);
  const rows =
    scenario === "empty" || scenario === "abstention"
      ? []
      : horizons.map((hours) => {
          const p50 = soilAt(device.id, new Date(issued.getTime() + hours * HOUR_MS), thresholds).moisture;
          const band = 2 + hours / 12;
          return { hours, p10: round(clamp(p50 - band, 0, 100), 1), p50, p90: round(clamp(p50 + band, 0, 100), 1) };
        });
  const first = rows[0];
  return {
    field_id: seed.id,
    device_id: device.id,
    issued_at: iso(issued),
    horizons: rows,
    thresholds: { ...thresholds },
    provenance: provenance("soil_forecast", scenario, now, {
      confidence: first ? interval(first.p10, first.p90, true) : NO_CONFIDENCE,
      dataAsOf: lastSeen(device, now),
    }),
  };
}

/* ---------- 3. irrigation_need ---------- */

const ABSTAIN_REASON = "Prévision trop incertaine : décision laissée aux seuils du kit.";
const RAIN_DEFER_PROBABILITY = 0.5;

interface WaterBalance {
  et0: number;
  etc: number;
  rain: number;
  rainProbability: number;
  rainThreshold: number;
  net: number;
}

function waterBalance(seed: FieldSeed, scenario: MockScenario, now: Date): WaterBalance {
  const today = weatherDays(seed.id, now, 1)[0];
  const et0 = scenario === "fallback" ? (today?.et0_hargreaves_mm ?? 5) : (today?.et0_mm ?? 5);
  const etc = round(et0 * cropKc(seed), 1);
  const rain = today?.precipitation_mm ?? 0;
  const net = seed.crop ? round(Math.max(0, etc - rain), 1) : 0;
  return { et0, etc, rain, rainProbability: today?.rain_probability ?? 0, rainThreshold: today?.rain_threshold_mm ?? 1, net };
}

export function irrigationNeed(seed: FieldSeed, scenario: MockScenario, now: Date): IrrigationNeed {
  const prov = (need: number) =>
    provenance("irrigation_need", scenario, now, { confidence: interval(round(need * 0.8, 1), round(need * 1.2, 1), true) });
  if (scenario === "empty") {
    return { field_id: seed.id, window_hours: 24, need_mm: 0, volume_m3: 0, defer: false, defer_reason: null, rain_expected_mm: 0, provenance: prov(0) };
  }
  const balance = waterBalance(seed, scenario, now);
  if (scenario === "abstention") {
    return { field_id: seed.id, window_hours: 24, need_mm: balance.net, volume_m3: null, defer: true, defer_reason: ABSTAIN_REASON, rain_expected_mm: null, provenance: prov(balance.net) };
  }
  const defer = balance.net > 0 && balance.rainProbability >= RAIN_DEFER_PROBABILITY && balance.rain >= balance.rainThreshold;
  return {
    field_id: seed.id,
    window_hours: 24,
    need_mm: balance.net,
    volume_m3: mmToM3(balance.net, seed.areaHa),
    defer,
    defer_reason: defer ? `Pluie probable (${Math.round(balance.rainProbability * 100)} %) : arrosage reporté.` : null,
    rain_expected_mm: balance.rain,
    provenance: prov(balance.net),
  };
}

/** Volume net du jour (m³) pour le planificateur ; 0 si l'arrosage est reporté. */
export function plannedVolume(seed: FieldSeed, scenario: MockScenario, now: Date): number {
  const need = irrigationNeed(seed, scenario === "fallback" ? "fallback" : "nominal", now);
  return need.defer ? 0 : (need.volume_m3 ?? 0);
}

/* ---------- 5. recommendations ---------- */

const FERT_CAVEAT = "Valeurs indicatives : sonde NPK non étalonnée, à confirmer par une analyse de sol.";
type IrrigationAction = "verifier_capteur" | "irriguer" | "surveiller" | "ne_pas_irriguer";

const ACTION_PRIORITY: Readonly<Record<IrrigationAction, "high" | "medium" | "low">> = {
  verifier_capteur: "high",
  irriguer: "high",
  surveiller: "medium",
  ne_pas_irriguer: "low",
};

const ACTION_REASON: Readonly<Record<IrrigationAction, string>> = {
  verifier_capteur: "Le kit ne transmet plus : vérifier l'alimentation et la sonde avant toute décision.",
  irriguer: "Humidité du sol sous le seuil de démarrage.",
  surveiller: "Humidité du sol entre les seuils : pas d'action immédiate.",
  ne_pas_irriguer: "Humidité du sol au-dessus du seuil d'arrêt.",
};

function irrigationAction(seed: FieldSeed, now: Date): { action: IrrigationAction; measured: Date | null; serial: string | null } {
  const reading = kitReading(seed, now);
  if (!reading) return { action: "surveiller", measured: null, serial: null };
  const { device, moisture, measuredAt } = reading;
  if (device.status !== "active") return { action: "verifier_capteur", measured: measuredAt, serial: device.serial };
  const thr = effectiveThresholds(device.id, now);
  const action: IrrigationAction = moisture < thr.start_pct ? "irriguer" : moisture > thr.stop_pct ? "ne_pas_irriguer" : "surveiller";
  return { action, measured: measuredAt, serial: device.serial };
}

function irrigationReco(seed: FieldSeed, scenario: MockScenario, now: Date): RecommendationView {
  const balance = waterBalance(seed, scenario, now);
  const { action, measured, serial } = irrigationAction(seed, now);
  const device = deviceSeedOfField(seed.id);
  const thr = device ? effectiveThresholds(device.id, now) : DEFAULT_THRESHOLDS;
  const gross = round(balance.net / IRRIGATION_EFFICIENCY[seed.irrigation], 1);
  const abstain = scenario === "abstention";
  return {
    id: `rec-${seed.id}-irr`,
    kind: "irrigation",
    engine_version: `${nominalModel("recommendations").name}@${nominalModel("recommendations").version}`,
    created_at: iso(floorHour(now)),
    priority: abstain ? null : ACTION_PRIORITY[action],
    valid_until: abstain ? null : iso(new Date(now.getTime() + DAY_MS)),
    justification: abstain ? null : `${ACTION_REASON[action]} ETc du jour ${balance.etc} mm.`,
    payload: {
      advice: {
        action,
        reason: ACTION_REASON[action],
        etc_mm: balance.etc,
        net_mm: balance.net,
        gross_mm: gross,
        volume_m3: mmToM3(gross, seed.areaHa),
        caveat: device ? "Le kit applique ses propres seuils : ce conseil ne commande pas la pompe." : "Parcelle sans kit : conseil fondé sur la seule météo.",
      },
      crop: seed.crop,
      et0_mm: balance.et0,
      et0_method: scenario === "fallback" ? "hargreaves" : "penman-monteith (FAO-56)",
      thresholds: { ...thr, source: device ? "kit" : "défaut" },
      measured_at: measured ? iso(measured) : null,
      device_serial: serial,
    },
    provenance: provenance("recommendations", scenario, now, { dataAsOf: measured }),
  };
}

type NutrientLevel = "bas" | "moyen" | "eleve";
const LEVELS: Readonly<Record<"N" | "P" | "K", readonly [number, number]>> = { N: [20, 50], P: [10, 25], K: [80, 150] };
const NUTRIENT_LABEL = { N: "Azote", P: "Phosphore", K: "Potassium" } as const;

const levelOf = (nutrient: "N" | "P" | "K", value: number): NutrientLevel => {
  const [low, high] = LEVELS[nutrient];
  return value < low ? "bas" : value < high ? "moyen" : "eleve";
};

function fertilizationReco(seed: FieldSeed, scenario: MockScenario, now: Date): RecommendationView | null {
  const reading = kitReading(seed, now);
  if (!reading) return null;
  const npk = npkAt(reading.device.id, reading.device.npk, reading.measuredAt);
  const abstain = scenario === "abstention";
  const values = { N: npk.n, P: npk.p, K: npk.k } as const;
  const nutrients = (Object.keys(values) as ("N" | "P" | "K")[]).map((key) => {
    const level = levelOf(key, values[key]);
    return {
      nutrient: key,
      value: values[key],
      level: abstain ? null : level,
      message: level === "bas" ? `${NUTRIENT_LABEL[key]} indicatif bas : à confirmer avant tout apport.` : `${NUTRIENT_LABEL[key]} indicatif ${level}.`,
    };
  });
  const anyLow = nutrients.some((n) => levelOf(n.nutrient as "N" | "P" | "K", n.value ?? 0) === "bas");
  return {
    id: `rec-${seed.id}-fert`,
    kind: "fertilization",
    engine_version: `${nominalModel("recommendations").name}@${nominalModel("recommendations").version}`,
    created_at: iso(floorHour(now)),
    priority: abstain ? null : anyLow ? "medium" : "low",
    valid_until: abstain ? null : iso(new Date(now.getTime() + 7 * DAY_MS)),
    justification: abstain ? null : anyLow ? "Au moins un élément indicatif bas d'après la sonde NPK." : "Éléments NPK indicatifs suffisants.",
    payload: { nutrients, sensor_ok: reading.device.status === "active", caveat: FERT_CAVEAT },
    provenance: provenance("recommendations", scenario, now, { dataAsOf: reading.measuredAt }),
  };
}

export function recommendations(seed: FieldSeed, scenario: MockScenario, now: Date): RecommendationView[] {
  if (scenario === "empty") return [];
  const hasKit = deviceSeedOfField(seed.id) !== null;
  if (!hasKit && !seed.crop) return [];
  const fert = fertilizationReco(seed, scenario, now);
  return fert ? [irrigationReco(seed, scenario, now), fert] : [irrigationReco(seed, scenario, now)];
}

/** rec-<parcelle>-irr|fert → identifiant de parcelle ; null si l'identifiant n'est pas simulé. */
export function fieldIdOfRecommendation(recommendationId: string): string | null {
  const match = /^rec-(.+)-(irr|fert)$/.exec(recommendationId);
  return match?.[1] ?? null;
}

/* ---------- 6. fertilization ---------- */

const DOSES_KG_HA: Readonly<Record<string, { n: number; p: number; k: number }>> = {
  oignon: { n: 120, p: 60, k: 120 },
  tomate: { n: 150, p: 80, k: 200 },
  chou: { n: 150, p: 60, k: 150 },
  carotte: { n: 100, p: 80, k: 150 },
  "pomme de terre": { n: 160, p: 80, k: 200 },
};
const CLASS_FACTOR: Readonly<Record<NutrientLevel, number>> = { bas: 1.2, moyen: 1, eleve: 0.8 };

function npkClass(seed: FieldSeed, now: Date): NutrientLevel | null {
  const reading = kitReading(seed, now);
  if (!reading) return null;
  const npk = npkAt(reading.device.id, reading.device.npk, reading.measuredAt);
  const levels = [levelOf("N", npk.n), levelOf("P", npk.p), levelOf("K", npk.k)];
  if (levels.includes("bas")) return "bas";
  return levels.every((l) => l === "eleve") ? "eleve" : "moyen";
}

export function fertilization(seed: FieldSeed, scenario: MockScenario, now: Date): Fertilization {
  const base = seed.crop ? DOSES_KG_HA[seed.crop] : undefined;
  const cls = scenario === "abstention" ? null : npkClass(seed, now);
  const factor = CLASS_FACTOR[cls ?? "moyen"];
  const dose = (value: number | undefined) =>
    value === undefined || scenario === "empty" || scenario === "abstention" ? null : Math.round(value * factor);
  return {
    field_id: seed.id,
    crop: seed.crop,
    stage: seed.crop ? bbchStage(seed.plantedDaysAgo, seed.cycleDays).label : null,
    n_kg_ha: dose(base?.n),
    p_kg_ha: dose(base?.p),
    k_kg_ha: dose(base?.k),
    npk_class: cls,
    indicative: true,
    caveat: FERT_CAVEAT,
    provenance: provenance("fertilization", scenario, now, { dataAsOf: kitReading(seed, now)?.measuredAt ?? null }),
  };
}

/* ---------- 9. pest_risk ---------- */

const PEST_FACTORS = ["température moyenne favorable (26–30 °C)", "humidité relative nocturne > 70 %", "stade sensible de la culture"];

export function pestRisk(seed: FieldSeed, scenario: MockScenario, now: Date): PestRisk {
  const day = isoDay(now);
  const pests =
    scenario === "empty"
      ? []
      : pestsOf(seed).map((pest) => {
          const p7 = round(between(`${seed.id}:${pest}:${day}`, 0.08, 0.6), 2);
          const level: "low" | "medium" | "high" = p7 >= 0.5 ? "high" : p7 >= 0.25 ? "medium" : "low";
          const hideP = degraded(scenario);
          return {
            pest_code: pest,
            level,
            p_outbreak_7d: hideP ? null : p7,
            p_outbreak_14d: hideP ? null : round(Math.min(1, p7 * 1.3), 2),
            factors: PEST_FACTORS.slice(0, level === "low" ? 1 : level === "medium" ? 2 : 3),
          };
        });
  const maxP = pests.reduce<number | null>((acc, p) => (p.p_outbreak_7d === null ? acc : Math.max(acc ?? 0, p.p_outbreak_7d)), null);
  return {
    field_id: seed.id,
    pests,
    provenance: provenance("pest_risk", scenario, now, { confidence: maxP === null ? NO_CONFIDENCE : probability(maxP, false) }),
  };
}

/* ---------- 11. vegetation ---------- */

export const VEGETATION_DEFAULT_DAYS = 90;
export const VEGETATION_MAX_DAYS = 400;

export function vegetation(seed: FieldSeed, from: Date, to: Date, scenario: MockScenario, now: Date): Vegetation {
  const points = scenario === "empty" ? [] : ndviSeries(seed.id, plantedDate(seed, now), from, to);
  const series = points.map((p) =>
    scenario === "fallback" && p.gapfilled ? { ...p, ndvi: null, evi: null } : p,
  );
  const lastNdvi = [...series].reverse().find((p) => p.ndvi !== null)?.ndvi ?? null;
  const abstain = scenario === "abstention";
  const lastDate = series[series.length - 1]?.date;
  return {
    field_id: seed.id,
    from: isoDay(from),
    to: isoDay(to),
    series,
    stage: abstain || !seed.crop ? null : bbchStage(seed.plantedDaysAgo, seed.cycleDays),
    canopy_cover_pct: abstain || lastNdvi === null ? null : Math.round(clamp(((lastNdvi - 0.15) / 0.65) * 100, 0, 100)),
    provenance: provenance("vegetation", scenario, now, { dataAsOf: lastDate ? new Date(`${lastDate}T10:30:00Z`) : null }),
  };
}

/** Dernier NDVI connu (couche « field » de la carte). */
export function latestNdvi(seed: FieldSeed, now: Date): number | null {
  const points = ndviSeries(seed.id, plantedDate(seed, now), new Date(now.getTime() - 15 * DAY_MS), now);
  return points[points.length - 1]?.ndvi ?? null;
}

/* ---------- 12. yield_forecast ---------- */

const BASE_YIELD_T_HA: Readonly<Record<string, number>> = { oignon: 25, tomate: 30, chou: 35, carotte: 28, "pomme de terre": 22 };
const YIELD_CAVEAT =
  "Prévision expérimentale : validation leave-one-season-out sur peu de saisons ; ne pas l'utiliser pour un engagement commercial.";

/** null : pas de cycle actif (404 NO_ACTIVE_CYCLE). */
export function yieldForecast(seed: FieldSeed, scenario: MockScenario, now: Date): YieldForecast | null {
  const cycle = activeCycle(seed, now);
  if (!cycle || !seed.crop || scenario === "empty") return null;
  const base = BASE_YIELD_T_HA[seed.crop] ?? 20;
  const predicted = round(base * between(`${seed.id}:yield`, 0.85, 1.05), 1);
  const p10 = round(predicted * 0.8, 1);
  const p90 = round(predicted * 1.15, 1);
  const prov = provenance("yield_forecast", scenario, now, { confidence: interval(p10, p90, false) });
  return {
    field_id: seed.id,
    crop_cycle: { id: cycle.id, crop: cycle.crop, status: cycle.status, planted_on: cycle.planted_on },
    forecast:
      scenario === "abstention"
        ? null
        : { id: `yf-${seed.id}`, model_name: prov.model_name, model_version: prov.model_version, predicted_t_ha: predicted, p10, p90, created_at: prov.computed_at },
    actual_t_ha: null,
    caveat: YIELD_CAVEAT,
    provenance: prov,
  };
}

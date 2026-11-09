/**
 * Séries simulées déterministes : même entrée (identifiant, horodatage) → même valeur, d'un appel et d'un
 * processus à l'autre. Aucune dépendance à Math.random : FNV-1a pour la graine, mulberry32 pour le tirage.
 */
import type { Bucket, Measurement, SeriesRow, ThresholdPair } from "@/lib/types";

import { DAY_MS, HOUR_MS, addDays, floorHour, iso, isoDay, round } from "../base";

/* ---------- Pseudo-aléa ---------- */

export function hash32(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

export function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4_294_967_296;
  };
}

/** Tirage uniforme [0, 1) attaché à une clé. */
export const rand = (key: string): number => mulberry32(hash32(key))();

/** Tirage uniforme [min, max). */
export const between = (key: string, min: number, max: number): number => min + (max - min) * rand(key);

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

/* ---------- Kit : humidité du sol, air, NPK ---------- */

/** Période du cycle séchage → arrosage (h) ; l'arrosage remonte de start à stop en une heure. */
const SOIL_CYCLE_H = 30;
const NOISE_PCT = 1.5;

export interface SoilSample {
  moisture: number;
  pumpOn: boolean;
}

export function soilAt(seedId: string, at: Date, thresholds: ThresholdPair): SoilSample {
  const phase = rand(`${seedId}:phase`) * SOIL_CYCLE_H;
  const hours = at.getTime() / HOUR_MS + phase;
  const pos = ((hours % SOIL_CYCLE_H) + SOIL_CYCLE_H) % SOIL_CYCLE_H;
  const span = thresholds.stop_pct - thresholds.start_pct;
  const pumpOn = pos < 1;
  const base = pumpOn
    ? thresholds.start_pct + span * pos
    : thresholds.stop_pct - (span + 3) * ((pos - 1) / (SOIL_CYCLE_H - 1));
  const noise = (rand(`${seedId}:${Math.floor(at.getTime() / (15 * 60_000))}`) - 0.5) * 2 * NOISE_PCT;
  return { moisture: round(clamp(base + noise, 0, 100), 1), pumpOn };
}

/** Température de l'air (°C) : maximum vers 15 h UTC (= heure locale au Sénégal). */
export function airTempAt(seedId: string, at: Date): number {
  const hour = at.getUTCHours() + at.getUTCMinutes() / 60;
  const offset = between(`${seedId}:t-offset`, -0.8, 0.8);
  return round(22 + 8 * Math.sin((2 * Math.PI * (hour - 9)) / 24) + offset, 1);
}

export function airHumidityAt(seedId: string, at: Date): number {
  const hour = at.getUTCHours() + at.getUTCMinutes() / 60;
  return round(clamp(62 - 22 * Math.sin((2 * Math.PI * (hour - 9)) / 24) + between(`${seedId}:h-offset`, -4, 4), 5, 100), 1);
}

export interface NpkBase {
  n: number;
  p: number;
  k: number;
}

/** Seuils indicatifs du firmware v1.1 (N < 20, P < 10, K < 80 mg/kg) : affichés, jamais recalculés côté page. */
export const npkLow = (npk: NpkBase): boolean => npk.n < 20 || npk.p < 10 || npk.k < 80;

export function npkAt(seedId: string, base: NpkBase, at: Date): NpkBase {
  const day = isoDay(at);
  const jitter = (key: string, value: number) => Math.round(value * between(`${seedId}:${key}:${day}`, 0.97, 1.03));
  return { n: jitter("n", base.n), p: jitter("p", base.p), k: jitter("k", base.k) };
}

export function latestMeasurement(
  seedId: string,
  at: Date,
  thresholds: ThresholdPair,
  npkBase: NpkBase,
  firmware: string,
): Measurement {
  const soil = soilAt(seedId, at, thresholds);
  const npk = npkAt(seedId, npkBase, at);
  return {
    ts: iso(at),
    source: "relay",
    fw: firmware,
    soil_moisture_pct: soil.moisture,
    air_temp_c: airTempAt(seedId, at),
    air_humidity_pct: airHumidityAt(seedId, at),
    pressure_hpa: round(1011 + between(`${seedId}:p:${isoDay(at)}`, -2, 2), 1),
    n_mgkg: npk.n,
    p_mgkg: npk.p,
    k_mgkg: npk.k,
    pump_on: soil.pumpOn,
    pump_fault: false,
    soil_sensor_ok: true,
    bme_ok: true,
    npk_ok: true,
    alert_fertilizer: npkLow(npk),
    alert_plant: false,
    threshold_start_pct: thresholds.start_pct,
    threshold_stop_pct: thresholds.stop_pct,
  };
}

/* ---------- Agrégats de mesures ---------- */

export const MAX_SERIES_ROWS = 400;

const BUCKET_MS: Record<Exclude<Bucket, "raw">, number> = {
  "1h": HOUR_MS,
  "1d": DAY_MS,
  "1w": 7 * DAY_MS,
  "1mo": 30 * DAY_MS,
};
const RAW_STEP_MS = 15 * 60_000;
/** Échantillons par intervalle : au plus 24, pour borner le coût des agrégats longs. */
const SAMPLES_PER_BUCKET = 24;

export interface SeriesResult {
  rows: SeriesRow[];
  truncated: boolean;
}

/** Lignes d'un kit sur [from, to), jamais au-delà de son dernier contact (`until`). */
export function measurementRows(
  seedId: string,
  thresholds: ThresholdPair,
  bucket: Bucket,
  from: Date,
  to: Date,
  until: Date,
): SeriesResult {
  const end = Math.min(to.getTime(), until.getTime());
  const step = bucket === "raw" ? RAW_STEP_MS : BUCKET_MS[bucket];
  const start = Math.ceil(from.getTime() / step) * step;
  const rows: SeriesRow[] = [];
  for (let t = start; t < end; t += step) {
    rows.push(bucket === "raw" ? rawRow(seedId, thresholds, new Date(t)) : aggregateRow(seedId, thresholds, t, step, end));
  }
  const truncated = rows.length > MAX_SERIES_ROWS;
  return { rows: truncated ? rows.slice(-MAX_SERIES_ROWS) : rows, truncated };
}

function rawRow(seedId: string, thresholds: ThresholdPair, at: Date): SeriesRow {
  const soil = soilAt(seedId, at, thresholds);
  return {
    ts: iso(at),
    soil_moisture_pct: soil.moisture,
    air_temp_c: airTempAt(seedId, at),
    air_humidity_pct: airHumidityAt(seedId, at),
    pump_on: soil.pumpOn,
  };
}

function aggregateRow(seedId: string, thresholds: ThresholdPair, start: number, step: number, end: number): SeriesRow {
  const span = Math.min(step, end - start);
  const n = Math.max(1, Math.min(SAMPLES_PER_BUCKET, Math.round(span / RAW_STEP_MS)));
  const soil: number[] = [];
  const temp: number[] = [];
  const hum: number[] = [];
  let pumpOn = 0;
  for (let i = 0; i < n; i += 1) {
    const at = new Date(start + (span * i) / n);
    const sample = soilAt(seedId, at, thresholds);
    soil.push(sample.moisture);
    temp.push(airTempAt(seedId, at));
    hum.push(airHumidityAt(seedId, at));
    if (sample.pumpOn) pumpOn += 1;
  }
  const avg = (values: number[]) => round(values.reduce((a, b) => a + b, 0) / values.length, 1);
  return {
    ts: iso(new Date(start)),
    n_points: Math.max(1, Math.round(span / (5 * 60_000))),
    soil_moisture_pct_avg: avg(soil),
    soil_moisture_pct_min: Math.min(...soil),
    soil_moisture_pct_max: Math.max(...soil),
    air_temp_c_avg: avg(temp),
    air_humidity_pct_avg: avg(hum),
    pump_on_ratio: round(pumpOn / n, 2),
  };
}

/* ---------- Météo ---------- */

export interface WeatherDaySample {
  date: string;
  t_max_c: number;
  t_min_c: number;
  precipitation_mm: number;
  et0_mm: number;
  et0_hargreaves_mm: number;
  rain_probability: number;
  rain_threshold_mm: number;
  local_bias_c: number;
}

export function weatherDays(seedId: string, now: Date, days: number): WeatherDaySample[] {
  return Array.from({ length: days }, (_, i) => {
    const date = isoDay(addDays(now, i));
    const key = `${seedId}:wx:${date}`;
    const rainy = rand(`${key}:rain`) < 0.12;
    const et0 = round(between(`${key}:et0`, 4.5, 6), 1);
    return {
      date,
      t_max_c: round(between(`${key}:tmax`, 30, 34), 1),
      t_min_c: round(between(`${key}:tmin`, 18, 21), 1),
      precipitation_mm: rainy ? round(between(`${key}:mm`, 0.5, 4), 1) : 0,
      et0_mm: et0,
      et0_hargreaves_mm: round(et0 + between(`${key}:hg`, 0.1, 0.6), 1),
      rain_probability: round(rainy ? between(`${key}:p`, 0.45, 0.7) : between(`${key}:p`, 0.05, 0.35), 2),
      rain_threshold_mm: 1,
      local_bias_c: -0.6,
    };
  });
}

/* ---------- Végétation (NDVI Sentinel-2, tous les 5 jours) ---------- */

const NDVI_STEP_DAYS = 5;
const BARE_SOIL_NDVI = 0.14;

/** Courbe logistique de croissance ; sol nu avant semis ou sans culture. */
export function ndviAt(seedId: string, daysSincePlanting: number | null, date: string): number {
  const noise = between(`${seedId}:ndvi:${date}`, -0.02, 0.02);
  if (daysSincePlanting === null || daysSincePlanting < 0) return round(BARE_SOIL_NDVI + noise, 3);
  return round(0.15 + 0.65 / (1 + Math.exp(-(daysSincePlanting - 35) / 8)) + noise, 3);
}

export interface NdviPoint {
  date: string;
  ndvi: number | null;
  evi: number | null;
  gapfilled: boolean;
}

export function ndviSeries(seedId: string, plantedOn: Date | null, from: Date, to: Date): NdviPoint[] {
  const points: NdviPoint[] = [];
  const first = Math.ceil(from.getTime() / (NDVI_STEP_DAYS * DAY_MS)) * NDVI_STEP_DAYS * DAY_MS;
  for (let t = first; t <= to.getTime(); t += NDVI_STEP_DAYS * DAY_MS) {
    const date = isoDay(new Date(t));
    const since = plantedOn ? Math.floor((t - plantedOn.getTime()) / DAY_MS) : null;
    const ndvi = ndviAt(seedId, since, date);
    points.push({ date, ndvi, evi: round(ndvi * 0.6, 3), gapfilled: rand(`${seedId}:cloud:${date}`) < 0.2 });
  }
  return points;
}

/** Stade BBCH approximatif d'après les jours depuis le semis (barème générique maraîcher). */
export function bbchStage(daysSincePlanting: number, cycleDays: number): { bbch: number; label: string } {
  const share = cycleDays > 0 ? daysSincePlanting / cycleDays : 0;
  if (share < 0.15) return { bbch: 12, label: "Levée, premières feuilles" };
  if (share < 0.45) return { bbch: 35, label: "Croissance végétative" };
  if (share < 0.75) return { bbch: 55, label: "Développement des organes récoltés" };
  return { bbch: 79, label: "Maturation" };
}

export const hourNow = (now: Date): Date => floorHour(now);

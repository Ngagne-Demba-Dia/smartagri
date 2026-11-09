/**
 * Calculs partagés par les constructeurs de réponses simulées : coefficient cultural, efficience
 * d'irrigation, humidité courante d'une parcelle. Aucun n'écrit dans l'état de la simulation.
 */
import type { IrrigationType } from "@/lib/types";

import { DAY_MS, round } from "../base";
import { deviceSeedOfField, lastSeen, type DeviceSeed, type FieldSeed } from "../fixtures/places";
import { soilAt } from "../fixtures/series";
import { effectiveThresholds } from "../store";

/** Kc de mi-saison (FAO-56, tableau 12) ; réduit en début et fin de cycle. */
const KC_MID: Readonly<Record<string, number>> = {
  oignon: 1.05,
  tomate: 1.15,
  chou: 1.05,
  carotte: 1.05,
  "pomme de terre": 1.15,
};
const KC_INITIAL_FACTOR = 0.6;
const KC_LATE_FACTOR = 0.8;
const KC_BARE_SOIL = 0.3;

export function cropKc(seed: FieldSeed): number {
  if (!seed.crop) return KC_BARE_SOIL;
  const mid = KC_MID[seed.crop] ?? 1;
  const share = seed.cycleDays > 0 ? seed.plantedDaysAgo / seed.cycleDays : 0;
  if (share < 0.15) return round(mid * KC_INITIAL_FACTOR, 2);
  if (share > 0.8) return round(mid * KC_LATE_FACTOR, 2);
  return mid;
}

/** Efficience d'application par mode d'irrigation (brut = net / efficience). */
export const IRRIGATION_EFFICIENCY: Readonly<Record<IrrigationType, number>> = {
  drip: 0.9,
  sprinkler: 0.75,
  furrow: 0.6,
  manual: 0.7,
};

/** 1 mm sur 1 ha = 10 m³. */
export const mmToM3 = (mm: number, areaHa: number): number => round(mm * areaHa * 10, 1);

export function plantedDate(seed: FieldSeed, now: Date): Date | null {
  return seed.crop ? new Date(now.getTime() - seed.plantedDaysAgo * DAY_MS) : null;
}

export interface KitReading {
  device: DeviceSeed;
  moisture: number;
  measuredAt: Date;
}

/** Dernière humidité connue de la parcelle (kit associé), null sans kit. */
export function kitReading(seed: FieldSeed, now: Date): KitReading | null {
  const device = deviceSeedOfField(seed.id);
  if (!device) return null;
  const measuredAt = lastSeen(device, now);
  const { moisture } = soilAt(device.id, measuredAt, effectiveThresholds(device.id, now));
  return { device, moisture, measuredAt };
}

export const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));

/** Ravageurs suivis par culture (pest_phenology, doc 14). */
export const CROP_PESTS: Readonly<Record<string, readonly string[]>> = {
  oignon: ["thrips_tabaci"],
  tomate: ["tuta_absoluta", "helicoverpa_armigera"],
  chou: ["plutella_xylostella"],
  carotte: [],
  "pomme de terre": ["phthorimaea_operculella"],
};

export const pestsOf = (seed: FieldSeed): readonly string[] => (seed.crop ? (CROP_PESTS[seed.crop] ?? []) : []);

/**
 * Périodes des courbes J/S/M/A (doc 10, module 3) et pas d'agrégation demandé à l'API
 * (GET /v1/devices/{id}/measurements?from=&to=&bucket=, CONVENTIONS §5).
 */
import type { Bucket, SeriesRow } from "./types";

export type RangeKey = "day" | "week" | "month" | "year";

export const RANGES: Record<RangeKey, { bucket: Bucket; hours: number }> = {
  day: { bucket: "1h", hours: 24 },
  week: { bucket: "1h", hours: 7 * 24 },
  month: { bucket: "1d", hours: 30 * 24 },
  year: { bucket: "1w", hours: 365 * 24 },
};

export const RANGE_KEYS: readonly RangeKey[] = ["day", "week", "month", "year"];

/** Fenêtre [from, to) en ISO 8601 UTC, arrondie à la minute pour stabiliser la clé de cache. */
export function rangeWindow(key: RangeKey, now: Date = new Date()): { from: string; to: string; bucket: Bucket } {
  const spec = RANGES[key];
  const to = new Date(Math.floor(now.getTime() / 60_000) * 60_000);
  const from = new Date(to.getTime() - spec.hours * 3_600_000);
  return { from: from.toISOString(), to: to.toISOString(), bucket: spec.bucket };
}

/** Humidité du sol d'une ligne : moyenne si agrégée, valeur brute sinon ; null si absente. */
export function soilMoisture(row: SeriesRow): number | null {
  const value = row.soil_moisture_pct_avg ?? row.soil_moisture_pct ?? null;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

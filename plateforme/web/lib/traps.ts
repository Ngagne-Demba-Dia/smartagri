/** Comptage de ravageurs par piège photo (service 10) : totaux journaliers et tendance. */
import type { TrapCounts } from "./contracts/device";

export type TrapPoint = TrapCounts["series"][number];
export type TrapTrend = "up" | "down" | "flat";

/** Somme des captures par jour (UTC), ordre chronologique. */
export function dailyTotals(series: readonly TrapPoint[]): Array<{ day: string; count: number }> {
  const byDay = new Map<string, number>();
  for (const point of series) {
    const day = point.captured_at.slice(0, 10);
    byDay.set(day, (byDay.get(day) ?? 0) + point.count);
  }
  return [...byDay.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([day, count]) => ({ day, count }));
}

export function trapTotal(series: readonly TrapPoint[]): number {
  return series.reduce((sum, p) => sum + p.count, 0);
}

const TREND_THRESHOLD = 0.15;

/** Moyenne journalière de la seconde moitié de la période comparée à la première ; null sous 4 jours. */
export function trapTrend(days: ReadonlyArray<{ count: number }>): TrapTrend | null {
  if (days.length < 4) return null;
  const half = Math.floor(days.length / 2);
  const mean = (part: ReadonlyArray<{ count: number }>) =>
    part.reduce((s, d) => s + d.count, 0) / part.length;
  const before = mean(days.slice(0, half));
  const after = mean(days.slice(days.length - half));
  if (before === 0 && after === 0) return "flat";
  if (before === 0) return "up";
  const change = (after - before) / before;
  if (change > TREND_THRESHOLD) return "up";
  if (change < -TREND_THRESHOLD) return "down";
  return "flat";
}

/** Photos du piège dans la série (les relevés qui portent une image). */
export function photoCount(series: readonly TrapPoint[]): number {
  return series.filter((p) => p.image_id !== null).length;
}

/**
 * Prévision d'humidité du sol (service 2) : mise en forme pure de {hours, p10, p50, p90}.
 * Aucune valeur n'est inventée : sans kit sur la parcelle, `horizons` est vide et l'écran le dit.
 */
import type { SoilForecast } from "./contracts/field";

export type SoilHorizon = SoilForecast["horizons"][number];
export type SoilThresholds = NonNullable<SoilForecast["thresholds"]>;

/** Position de la valeur médiane par rapport aux seuils réglés sur le kit. */
export type SoilStatus = "below_start" | "between" | "above_stop";

export function sortedHorizons(horizons: readonly SoilHorizon[]): SoilHorizon[] {
  return [...horizons].sort((a, b) => a.hours - b.hours);
}

export function soilStatus(value: number, thresholds: SoilThresholds | null): SoilStatus | null {
  if (!thresholds) return null;
  if (value < thresholds.start_pct) return "below_start";
  if (value > thresholds.stop_pct) return "above_stop";
  return "between";
}

/** Premier horizon dont la médiane passe sous le seuil de démarrage ; null si aucun (ou sans seuil). */
export function firstBelowStart(
  horizons: readonly SoilHorizon[],
  thresholds: SoilThresholds | null,
): SoilHorizon | null {
  if (!thresholds) return null;
  return sortedHorizons(horizons).find((h) => h.p50 < thresholds.start_pct) ?? null;
}

/** Plage globale p10–p90, pour le résumé accessible du graphique. */
export function forecastRange(horizons: readonly SoilHorizon[]): { low: number; high: number } | null {
  if (horizons.length === 0) return null;
  return {
    low: Math.min(...horizons.map((h) => h.p10)),
    high: Math.max(...horizons.map((h) => h.p90)),
  };
}

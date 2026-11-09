/** Calculs d'affichage de l'écran Irrigation (doc 18 §3) : ce ne sont pas des sorties du modèle. */
import type { IrrigationNeed } from "@/lib/contracts/field";
import { provenanceState } from "@/lib/contracts/provenance";
import type { WeatherDay } from "@/lib/types";

export interface ClimaticDemand {
  /** Σ ET0 − Σ pluie, ramené à 0 si négatif (mm). */
  demandMm: number;
  etMm: number;
  rainMm: number;
  /** Jours où l'ET0 et la pluie existent tous les deux. */
  daysCounted: number;
}

/** Demande climatique : seuls les jours où les deux valeurs existent comptent ; null s'il n'y en a aucun. */
export function climaticDemand(days: readonly WeatherDay[]): ClimaticDemand | null {
  const usable = days.filter((d) => d.et0_mm !== null && d.precipitation_mm !== null);
  if (usable.length === 0) return null;
  const etMm = usable.reduce((acc, d) => acc + (d.et0_mm ?? 0), 0);
  const rainMm = usable.reduce((acc, d) => acc + (d.precipitation_mm ?? 0), 0);
  return { demandMm: Math.max(0, etMm - rainMm), etMm, rainMm, daysCounted: usable.length };
}

export type ReadingKind = "deferred" | "abstained" | "none" | "needed";

/** « Lecture du résultat » : cas décrit par les champs du contrat, jamais une explication produite par un modèle. */
export function readingKind(need: IrrigationNeed): ReadingKind {
  if (need.defer && need.volume_m3 === null) return "abstained";
  if (need.defer) return "deferred";
  return need.need_mm === 0 ? "none" : "needed";
}

/** Vrai si le résultat est périmé ou en valeur de secours. */
export const isDegraded = (need: IrrigationNeed): boolean => provenanceState(need.provenance) !== "fresh";

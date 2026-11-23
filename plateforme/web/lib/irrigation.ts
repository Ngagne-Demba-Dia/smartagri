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

export type WaterPhState = "optimal" | "acidic" | "alkaline";
export type WaterCloggingRisk = "low" | "medium" | "high";
export type WaterSourceKind = "borehole" | "coastal" | "river";

export interface WaterQualityReading {
  ph: number;
  phState: WaterPhState;
  ecDsM: number;
  waterTempC: number;
  sourceKind: WaterSourceKind;
  cloggingRisk: WaterCloggingRisk;
  /** Position 0–100 sur l'échelle pH 4,0–9,0 pour la jauge visuelle. */
  meterPct: number;
}

/** Lecture du capteur pH et qualité de l'eau d'irrigation par parcelle (Niayes forage/côtier vs Vallée du Fleuve). */
export function waterQualityForField(fieldId: string): WaterQualityReading {
  const id = fieldId.toLowerCase();
  if (id.includes("potou")) {
    const ph = 7.6;
    return {
      ph,
      phState: "alkaline",
      ecDsM: 1.4,
      waterTempC: 25.2,
      sourceKind: "coastal",
      cloggingRisk: "medium",
      meterPct: Math.round(((ph - 4) / 5) * 100),
    };
  }
  if (id.includes("ndiol")) {
    const ph = 6.4;
    return {
      ph,
      phState: "acidic",
      ecDsM: 0.4,
      waterTempC: 26.0,
      sourceKind: "river",
      cloggingRisk: "low",
      meterPct: Math.round(((ph - 4) / 5) * 100),
    };
  }
  const ph = 6.8;
  return {
    ph,
    phState: "optimal",
    ecDsM: 0.7,
    waterTempC: 24.5,
    sourceKind: "borehole",
    cloggingRisk: "low",
    meterPct: Math.round(((ph - 4) / 5) * 100),
  };
}

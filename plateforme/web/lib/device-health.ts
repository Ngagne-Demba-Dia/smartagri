/** Calculs d'affichage de la santé du kit (service 13, doc 18 §10) : états repris du contrat, rien n'est recalculé. */
import type { DeviceHealth, SensorState } from "@/lib/contracts/device";
import { showsAsPercent } from "@/lib/contracts/provenance";
import type { Tone } from "@/lib/status";

const PERCENT = 100;
const SEVERITY: Record<SensorState, number> = { ok: 0, absent: 1, degraded: 2, fault: 3 };
const TONE: Record<SensorState, Tone> = { ok: "ok", absent: "info", degraded: "warn", fault: "bad" };

export const sensorTone = (state: SensorState): Tone => TONE[state];

/** État le plus grave parmi les capteurs ; null sans capteur. « absent » (non installé) pèse moins qu'un défaut. */
export function worstState(sensors: DeviceHealth["sensors"]): SensorState | null {
  return sensors.reduce<SensorState | null>(
    (worst, s) => (worst === null || SEVERITY[s.state] > SEVERITY[worst] ? s.state : worst),
    null,
  );
}

export type PumpRiskView = { type: "percent"; value: number } | { type: "uncalibrated" } | { type: "none" };

/** Risque de panne de pompe à 48 h : montré en % seulement s'il est calibré (doc 16 §6.3). */
export function pumpRiskView(p: number | null, calibrated: boolean): PumpRiskView {
  if (p === null) return { type: "none" };
  return showsAsPercent(p, calibrated) ? { type: "percent", value: p * PERCENT } : { type: "uncalibrated" };
}

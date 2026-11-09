/**
 * Verdicts (doc 10 §2, principe n° 1 : « le verdict avant les chiffres ») et états visuels.
 * Un état s'affiche toujours avec couleur + icône + mot (components/StatusTag.tsx).
 */
import type { AlertSeverity, Device, ThresholdPair } from "./types";

export type Tone = "ok" | "warn" | "bad" | "info";

export type MoistureVerdict = "dry" | "ok" | "wet" | "unknown";

/** Sous le seuil de démarrage : sol sec ; au-dessus du seuil d'arrêt : sol très humide. */
export function moistureVerdict(moisture: number | null | undefined, thresholds: ThresholdPair | null): MoistureVerdict {
  if (moisture == null || !thresholds) return "unknown";
  if (moisture < thresholds.start_pct) return "dry";
  if (moisture > thresholds.stop_pct) return "wet";
  return "ok";
}

export const VERDICT_TONE: Record<MoistureVerdict, Tone> = { dry: "bad", ok: "ok", wet: "warn", unknown: "info" };

export const SEVERITY_TONE: Record<AlertSeverity, Tone> = { critical: "bad", warning: "warn", info: "info" };

/** Kit vu il y a moins de 2 h : à jour ; moins de 24 h : en retard ; au-delà ou jamais : silencieux. */
export const FRESH_MS = 2 * 3_600_000;
export const STALE_MS = 24 * 3_600_000;

export type Freshness = "fresh" | "late" | "silent";

export function deviceFreshness(device: Pick<Device, "last_seen_at">, now: Date = new Date()): Freshness {
  if (!device.last_seen_at) return "silent";
  const age = now.getTime() - new Date(device.last_seen_at).getTime();
  if (Number.isNaN(age) || age > STALE_MS) return "silent";
  return age > FRESH_MS ? "late" : "fresh";
}

export const FRESHNESS_TONE: Record<Freshness, Tone> = { fresh: "ok", late: "warn", silent: "bad" };

/** Classe de la rampe séquentielle (0 = pas de mesure, 1 = sol sec … 5 = sol saturé), par pas de 20 %. */
export type RampStep = 0 | 1 | 2 | 3 | 4 | 5;

export function moistureRamp(moisture: number | null | undefined): RampStep {
  if (moisture == null || !Number.isFinite(moisture)) return 0;
  const clamped = Math.min(100, Math.max(0, moisture));
  return (Math.min(4, Math.floor(clamped / 20)) + 1) as RampStep;
}

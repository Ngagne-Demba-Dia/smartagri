/**
 * Règle des seuils d'irrigation, identique au firmware v1.1 et au backend
 * (backend/app/services/agronomy.py : validate_thresholds) :
 *   entiers ; 0 ≤ démarrage ; démarrage + 5 ≤ arrêt ≤ 100.
 * Comme le backend : un booléen n'est pas un entier ; une chaîne n'est acceptée que si elle contient
 * 1 à 3 chiffres (espaces autour tolérés) ; les nombres décimaux sont refusés.
 */
export const THRESHOLD_MIN_GAP = 5;
export const THRESHOLD_MAX = 100;
export const THRESHOLD_MIN = 0;

const INT_STRING = /^\d{1,3}$/;

export type ThresholdErrorCode = "not_integer" | "start_negative" | "gap_too_small" | "stop_above_max";

export interface ThresholdError {
  field: "start" | "stop";
  code: ThresholdErrorCode;
}

export type ThresholdValidation =
  | { ok: true; value: { start: number; stop: number } }
  | { ok: false; errors: ThresholdError[] };

/** Convertit une valeur brute en entier selon la règle du backend ; null si refusée. */
export function parseThresholdInt(value: unknown): number | null {
  if (typeof value === "boolean") return null;
  if (typeof value === "number") return Number.isSafeInteger(value) ? value : null;
  if (typeof value === "string") {
    const trimmed = value.trim();
    return INT_STRING.test(trimmed) ? Number.parseInt(trimmed, 10) : null;
  }
  return null;
}

export function thresholdsValid(start: number, stop: number): boolean {
  return THRESHOLD_MIN <= start && start + THRESHOLD_MIN_GAP <= stop && stop <= THRESHOLD_MAX;
}

/** Valide une paire brute (champs de formulaire ou JSON) et renvoie toutes les erreurs trouvées. */
export function validateThresholds(start: unknown, stop: unknown): ThresholdValidation {
  const startInt = parseThresholdInt(start);
  const stopInt = parseThresholdInt(stop);
  const errors: ThresholdError[] = [];

  if (startInt === null) errors.push({ field: "start", code: "not_integer" });
  if (stopInt === null) errors.push({ field: "stop", code: "not_integer" });
  if (startInt === null || stopInt === null) return { ok: false, errors };

  if (startInt < THRESHOLD_MIN) errors.push({ field: "start", code: "start_negative" });
  if (stopInt > THRESHOLD_MAX) errors.push({ field: "stop", code: "stop_above_max" });
  if (startInt + THRESHOLD_MIN_GAP > stopInt) errors.push({ field: "stop", code: "gap_too_small" });

  return errors.length === 0 ? { ok: true, value: { start: startInt, stop: stopInt } } : { ok: false, errors };
}

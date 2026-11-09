/**
 * Formats d'affichage : français du Sénégal, heure de Dakar (UTC+0, sans heure d'été).
 * Fonctions pures (aucune dépendance React) : testées dans tests/format.test.ts.
 */
export const DISPLAY_LOCALE = "fr-SN";
export const DISPLAY_TIME_ZONE = "Africa/Dakar";

/** Tiret cadratin pour toute valeur absente : jamais « 0 » ni « NaN » à la place d'une mesure manquante. */
export const MISSING = "—";

const MINUTE_MS = 60_000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export function parseIso(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatNumber(value: number | null | undefined, maxDigits = 0): string {
  if (value == null || !Number.isFinite(value)) return MISSING;
  return new Intl.NumberFormat(DISPLAY_LOCALE, { maximumFractionDigits: maxDigits }).format(value);
}

/** Pourcentage déjà exprimé en 0–100 (humidité, disponibilité) : « 42 % ». */
export function formatPct(value: number | null | undefined, maxDigits = 0): string {
  const text = formatNumber(value, maxDigits);
  return text === MISSING ? MISSING : `${text} %`;
}

export function formatDate(value: string | null | undefined): string {
  const date = parseIso(value);
  if (!date) return MISSING;
  return new Intl.DateTimeFormat(DISPLAY_LOCALE, {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: DISPLAY_TIME_ZONE,
  }).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  const date = parseIso(value);
  if (!date) return MISSING;
  return `${formatDate(value)}, ${formatClock(date)}`;
}

/** Heure à la française : « 9 h 12 ». */
export function formatClock(value: Date | string | null | undefined): string {
  const date = value instanceof Date ? value : parseIso(value);
  if (!date) return MISSING;
  const parts = new Intl.DateTimeFormat(DISPLAY_LOCALE, {
    hour: "numeric",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: DISPLAY_TIME_ZONE,
  }).formatToParts(date);
  const hour = parts.find((part) => part.type === "hour")?.value ?? "0";
  const minute = parts.find((part) => part.type === "minute")?.value ?? "00";
  return `${Number(hour)} h ${minute}`;
}

/** Jour court pour les axes de graphique : « lun. 27 ». */
export function formatWeekday(value: string | null | undefined): string {
  const date = parseIso(value);
  if (!date) return MISSING;
  return new Intl.DateTimeFormat(DISPLAY_LOCALE, { weekday: "short", day: "numeric", timeZone: DISPLAY_TIME_ZONE }).format(date);
}

export type AgeUnit = "now" | "minutes" | "hours" | "days";

/**
 * Âge d'un horodatage, à traduire par l'appelant (ex. t("common.ago.minutes", { count })).
 * Un horodatage dans le futur (horloge du kit ou du téléphone décalée) compte comme « à l'instant ».
 */
export function relativeAge(value: string | null | undefined, now: Date = new Date()): { unit: AgeUnit; count: number } | null {
  const date = parseIso(value);
  if (!date) return null;
  const age = now.getTime() - date.getTime();
  if (age < MINUTE_MS) return { unit: "now", count: 0 };
  if (age < HOUR_MS) return { unit: "minutes", count: Math.floor(age / MINUTE_MS) };
  if (age < DAY_MS) return { unit: "hours", count: Math.floor(age / HOUR_MS) };
  return { unit: "days", count: Math.floor(age / DAY_MS) };
}

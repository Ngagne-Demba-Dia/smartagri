/**
 * Fenêtres de dates des écrans à période (pièges, végétation, planning). Alignées sur le jour (UTC) :
 * la clé de cache TanStack ne change pas à chaque rendu et deux ouvertures du même jour partagent la requête.
 */
const DAY_MS = 86_400_000;

/** Jour calendaire « AAAA-MM-JJ » (UTC, identique à Africa/Dakar). */
export function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Fenêtre ISO date-heure [minuit il y a `days` jours ; minuit de demain), alignée sur le jour. */
export function dayAlignedWindow(now: Date, days: number): { from: string; to: string } {
  const startOfToday = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return {
    from: new Date(startOfToday - (days - 1) * DAY_MS).toISOString(),
    to: new Date(startOfToday + DAY_MS).toISOString(),
  };
}

/** Fenêtre en jours calendaires « AAAA-MM-JJ », bornes incluses. */
export function calendarWindow(now: Date, days: number): { from: string; to: string } {
  return { from: isoDay(new Date(now.getTime() - (days - 1) * DAY_MS)), to: isoDay(now) };
}

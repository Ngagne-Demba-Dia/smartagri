/**
 * Fenêtre des rapports : deux dates « AAAA-MM-JJ » (champs <input type="date">) converties en bornes
 * UTC ISO pour GET /v1/reports/kpis?from=&to= (le backend attend des datetime). Dakar est à UTC+0.
 */

export const DEFAULT_REPORT_DAYS = 30;
const DAY_MS = 86_400_000;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export interface DateRange {
  from: string;
  to: string;
}

export function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function defaultDateRange(now: Date, days: number = DEFAULT_REPORT_DAYS): DateRange {
  return { from: isoDay(new Date(now.getTime() - days * DAY_MS)), to: isoDay(now) };
}

/** null si une date est mal formée ou si le début suit la fin. */
export function toReportWindow(range: DateRange): { from: string; to: string } | null {
  if (!DATE_RE.test(range.from) || !DATE_RE.test(range.to)) return null;
  const from = `${range.from}T00:00:00Z`;
  const to = `${range.to}T23:59:59Z`;
  if (Number.isNaN(Date.parse(from)) || Number.isNaN(Date.parse(to)) || from > to) return null;
  return { from, to };
}

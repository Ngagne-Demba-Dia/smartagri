/**
 * Lecture des paramètres communs aux gestionnaires : corps JSON borné, fenêtre from/to,
 * périmètre d'un rapport KPI. Chaque fonction renvoie la valeur lue ou la réponse d'erreur à servir.
 */
import { UPLOAD_MAX_BYTES } from "@/lib/contracts/assistant";

import { visibleFarm, visibleField, visibleFieldSeeds } from "../access";
import type { Principal } from "../auth";
import { DAY_MS, fail, notFound } from "../base";
import type { KpiScope } from "../builders/org";
import { fieldSeedsOfFarm } from "../fixtures/places";
import { dateParam, invalid } from "../route";
import type { MockScenario } from "../scenario";

export const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const tooLarge = (scenario?: MockScenario): Response =>
  fail("PAYLOAD_TOO_LARGE", "Requête trop volumineuse.", 413, {
    details: { max_bytes: UPLOAD_MAX_BYTES },
    scenario,
  });

/** Corps JSON d'au plus UPLOAD_MAX_BYTES (même limite que le BFF) ; null si absent ou illisible. */
export async function readBoundedJson(request: Request): Promise<{ body: unknown } | "too_large"> {
  const text = await request.text();
  if (new TextEncoder().encode(text).length > UPLOAD_MAX_BYTES) return "too_large";
  if (text === "") return { body: null };
  try {
    return { body: JSON.parse(text) as unknown };
  } catch {
    return { body: null };
  }
}

export interface DateWindow {
  from: Date;
  to: Date;
}

/** Fenêtre ?from=&to= : `to` vaut maintenant et `from` vaut to − defaultDays par défaut. */
export function windowParams(query: URLSearchParams, now: Date, defaultDays: number, maxDays: number): DateWindow | Response {
  const to = query.has("to") ? dateParam(query, "to") : now;
  if (!to) return invalid("Date « to » illisible.");
  const from = query.has("from") ? dateParam(query, "from") : new Date(to.getTime() - defaultDays * DAY_MS);
  if (!from) return invalid("Date « from » illisible.");
  if (from.getTime() >= to.getTime()) return invalid("« from » doit précéder « to ».");
  if (to.getTime() - from.getTime() > maxDays * DAY_MS) {
    return invalid(`Fenêtre limitée à ${maxDays} jours.`, { max_days: maxDays });
  }
  return { from, to };
}

export const REPORT_DEFAULT_DAYS = 30;
export const REPORT_MAX_DAYS = 400;
const REPORT_SCOPES = ["org", "farm", "field"] as const;

export interface ReportRequest extends DateWindow {
  scope: KpiScope;
}

const isReportScope = (value: string): value is KpiScope["scope"] => (REPORT_SCOPES as readonly string[]).includes(value);

function reportScope(user: Principal, scope: KpiScope["scope"], scopeId: string | null): KpiScope | Response {
  if (scope === "org") {
    const orgId = scopeId ?? user.me.memberships[0]?.organization_id ?? null;
    if (!orgId || !user.orgIds.has(orgId)) return notFound();
    return { scope, scopeId: orgId, fields: visibleFieldSeeds(user).filter((f) => f.orgId === orgId) };
  }
  if (!scopeId) return invalid("« scope_id » obligatoire pour ce périmètre.");
  if (scope === "farm") {
    const farm = visibleFarm(user, scopeId);
    return farm ? { scope, scopeId, fields: fieldSeedsOfFarm(farm.id) } : notFound();
  }
  const field = visibleField(user, scopeId);
  return field ? { scope, scopeId, fields: [field] } : notFound();
}

/** ?scope=org|farm|field&scope_id=&from=&to= ; l'organisation par défaut est la première adhésion. */
export function reportRequest(user: Principal, query: URLSearchParams, now: Date): ReportRequest | Response {
  const scopeName = query.get("scope") ?? "org";
  if (!isReportScope(scopeName)) return invalid("« scope » vaut org, farm ou field.", { allowed: REPORT_SCOPES });
  const window = windowParams(query, now, REPORT_DEFAULT_DAYS, REPORT_MAX_DAYS);
  if (window instanceof Response) return window;
  const scope = reportScope(user, scopeName, query.get("scope_id"));
  return scope instanceof Response ? scope : { ...window, scope };
}

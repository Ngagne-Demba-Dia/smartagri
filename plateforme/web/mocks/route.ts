/**
 * Enveloppes des gestionnaires MSW. Ordre, identique pour toutes les routes :
 * authentification (401) → latence simulée → scénario error_503 (services d'IA) → résolveur.
 */
import { http, type HttpHandler } from "msw";

import { serviceById, type ServiceId } from "@/lib/contracts/registry";

import { principalFromRequest, type Principal } from "./auth";
import { CORE_LATENCY_MS, fail, simulateLatency, url } from "./base";
import { scenarioFor, type MockScenario } from "./scenario";

export type Method = "get" | "post" | "put";

export interface RouteContext {
  request: Request;
  params: Readonly<Record<string, string>>;
  query: URLSearchParams;
  user: Principal;
  now: Date;
}

export interface AiContext extends RouteContext {
  scenario: MockScenario;
}

type Resolver<C> = (ctx: C) => Response | Promise<Response>;

/** Code d'erreur 503 propre au service (doc 16 §9.3). */
const UNAVAILABLE: Partial<Record<ServiceId, string>> = {
  weather: "WEATHER_UNAVAILABLE",
  assistant_chat: "ASSISTANT_UNAVAILABLE",
  assistant_transcribe: "ASSISTANT_UNAVAILABLE",
};
const RETRY_AFTER_S = "30";

export const unauthenticated = (): Response => fail("UNAUTHENTICATED", "Session absente ou expirée.", 401);
export const forbidden = (): Response => fail("FORBIDDEN", "Action non autorisée pour ce rôle.", 403);

function stringParams(params: Record<string, string | readonly string[] | undefined>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(params)) {
    if (typeof value === "string") out[key] = value;
  }
  return out;
}

async function context(
  request: Request,
  params: Record<string, string | readonly string[] | undefined>,
  latencyMs: number,
): Promise<RouteContext | Response> {
  const user = principalFromRequest(request);
  if (!user) return unauthenticated();
  await simulateLatency(latencyMs);
  return { request, params: stringParams(params), query: new URL(request.url).searchParams, user, now: new Date() };
}

/** Route du socle (référentiel, mesures, seuils, alertes) : pas de scénario d'IA. */
export function coreRoute(method: Method, path: string, resolver: Resolver<RouteContext>): HttpHandler {
  return http[method](url(path), async ({ request, params }) => {
    const ctx = await context(request, params, CORE_LATENCY_MS);
    return ctx instanceof Response ? ctx : resolver(ctx);
  });
}

export interface AiRouteOptions {
  /**
   * « resolve » : le résolveur reçoit aussi le scénario error_503. Sert au service intégré à une route
   * existante (water_savings dans /v1/reports/kpis) : la route répond 200 et seul le bloc vaut null.
   */
  unavailable?: "fail" | "resolve";
}

/** Route d'un des 18 services : latence du registre et scénario courant du service. */
export function aiRoute(
  service: ServiceId,
  method: Method,
  path: string,
  resolver: Resolver<AiContext>,
  options: AiRouteOptions = {},
): HttpHandler {
  return http[method](url(path), async ({ request, params }) => {
    const ctx = await context(request, params, serviceById(service).mockLatencyMs);
    if (ctx instanceof Response) return ctx;
    const scenario = scenarioFor(service);
    if (scenario === "error_503" && options.unavailable !== "resolve") {
      const code = UNAVAILABLE[service] ?? "MODEL_UNAVAILABLE";
      return fail(code, "Service momentanément indisponible (simulation).", 503, {
        headers: { "Retry-After": RETRY_AFTER_S },
        scenario,
      });
    }
    return resolver({ ...ctx, scenario });
  });
}

/** Paramètre de requête entier borné ; `fallback` si absent, null si invalide. */
export function intParam(query: URLSearchParams, name: string, fallback: number, min: number, max: number): number | null {
  const raw = query.get(name);
  if (raw === null || raw === "") return fallback;
  if (!/^\d+$/.test(raw)) return null;
  const value = Number.parseInt(raw, 10);
  return value >= min && value <= max ? value : null;
}

/** Date ou date-heure ISO ; null si absente ou illisible. */
export function dateParam(query: URLSearchParams, name: string): Date | null {
  const raw = query.get(name);
  if (!raw) return null;
  const value = new Date(raw);
  return Number.isNaN(value.getTime()) ? null : value;
}

export const invalid = (message: string, details?: Record<string, unknown>): Response =>
  fail("VALIDATION_ERROR", message, 422, details ? { details } : {});

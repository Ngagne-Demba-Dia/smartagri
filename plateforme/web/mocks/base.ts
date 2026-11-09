/**
 * Briques communes des simulations : URL de base, enveloppe CONVENTIONS §5 marquée meta.mock = true,
 * latence simulée (doc 16 §9.5 : proche de la cible p95 de §9.4).
 */
import { HttpResponse } from "msw";

import { MOCK_BASE } from "@/lib/mock-config";

import type { MockScenario } from "./scenario";

export const url = (path: string): string => `${MOCK_BASE}${path}`;

/** Latence des routes non-IA (référentiel, mesures, session). */
export const CORE_LATENCY_MS = 120;
const MAX_LATENCY_FACTOR = 10;

/** AGRI_MOCK_LATENCY : facteur multiplicatif ; « 0 » supprime l'attente (tests). */
export function latencyFactor(): number {
  const raw = process.env.AGRI_MOCK_LATENCY;
  if (raw === undefined || raw.trim() === "") return 1;
  const value = Number(raw);
  return Number.isFinite(value) && value >= 0 ? Math.min(value, MAX_LATENCY_FACTOR) : 1;
}

export async function simulateLatency(ms: number): Promise<void> {
  const scaled = Math.round(ms * latencyFactor());
  if (scaled <= 0) return;
  await new Promise<void>((resolve) => setTimeout(resolve, scaled));
}

export interface MockMeta {
  scenario?: MockScenario;
  [key: string]: unknown;
}

export function ok<T>(data: T, meta: MockMeta = {}, status = 200): Response {
  return HttpResponse.json({ success: true, data, error: null, meta: { mock: true, ...meta } }, { status });
}

export interface FailOptions {
  headers?: Record<string, string>;
  details?: Record<string, unknown>;
  scenario?: MockScenario;
}

export function fail(code: string, message: string, status: number, options: FailOptions = {}): Response {
  const error = options.details ? { code, message, details: options.details } : { code, message };
  const meta = options.scenario ? { mock: true, scenario: options.scenario } : { mock: true };
  return HttpResponse.json({ success: false, data: null, error, meta }, { status, headers: options.headers });
}

export const notFound = (scenario?: MockScenario): Response =>
  fail("NOT_FOUND", "Ressource introuvable.", 404, { scenario });

/** Lecture tolérante du corps JSON : null si absent ou illisible (la validation zod tranche ensuite). */
export async function readJson(request: Request): Promise<unknown> {
  try {
    const text = await request.text();
    return text === "" ? null : (JSON.parse(text) as unknown);
  } catch {
    return null;
  }
}

/** Arrondi à n décimales, sans -0. */
export function round(value: number, digits = 1): number {
  const factor = 10 ** digits;
  const rounded = Math.round(value * factor) / factor;
  return Object.is(rounded, -0) ? 0 : rounded;
}

export const HOUR_MS = 3_600_000;
export const DAY_MS = 24 * HOUR_MS;

/** Heure pleine inférieure : les séries restent identiques d'un appel à l'autre dans l'heure. */
export function floorHour(date: Date): Date {
  return new Date(Math.floor(date.getTime() / HOUR_MS) * HOUR_MS);
}

export function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function addDays(date: Date, days: number): Date {
  return new Date(date.getTime() + days * DAY_MS);
}

/** Date ISO à la seconde, sans millisecondes (forme de l'API). */
export function iso(date: Date): string {
  return `${date.toISOString().slice(0, 19)}Z`;
}

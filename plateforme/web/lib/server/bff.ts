import "server-only";

import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS_COOKIE,
  ACCESS_EXPIRY_MARGIN_S,
  CSRF_HEADER,
  CSRF_HEADER_VALUE,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE_S,
  cookieOptions,
} from "@/lib/session-cookies";

import { upstreamBase, upstreamFetch } from "./upstream";

export { apiBaseUrl } from "./upstream";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
}

export function isTokenPair(value: unknown): value is TokenPair {
  if (typeof value !== "object" || value === null) return false;
  const pair = value as Record<string, unknown>;
  return (
    typeof pair.access_token === "string" &&
    typeof pair.refresh_token === "string" &&
    typeof pair.expires_in === "number" &&
    pair.expires_in > 0
  );
}

/** Réponse d'erreur au format de l'enveloppe, sans détail interne. */
export function envelopeError(code: string, message: string, status: number): NextResponse {
  return NextResponse.json({ success: false, data: null, error: { code, message }, meta: null }, { status });
}

export function envelopeOk<T>(data: T, status = 200): NextResponse {
  return NextResponse.json({ success: true, data, error: null, meta: null }, { status });
}

/**
 * Protection CSRF des routes mutantes (doc 10 §7) : en-tête X-Requested-With attendu (un formulaire
 * HTML d'un autre site ne peut pas le poser sans pré-vol CORS) et, si présent, Origin identique à l'hôte.
 * S'ajoute à SameSite=Strict sur les cookies.
 */
export function checkCsrf(request: NextRequest): NextResponse | null {
  if (request.headers.get(CSRF_HEADER) !== CSRF_HEADER_VALUE) {
    return envelopeError("CSRF_REJECTED", "Requête refusée.", 403);
  }
  const origin = request.headers.get("origin");
  if (origin && origin !== request.nextUrl.origin) {
    return envelopeError("CSRF_REJECTED", "Requête refusée.", 403);
  }
  return null;
}

export function setSessionCookies(response: NextResponse, pair: TokenPair): void {
  const accessMaxAge = Math.max(pair.expires_in - ACCESS_EXPIRY_MARGIN_S, 1);
  response.cookies.set(ACCESS_COOKIE, pair.access_token, cookieOptions(accessMaxAge));
  response.cookies.set(REFRESH_COOKIE, pair.refresh_token, cookieOptions(REFRESH_MAX_AGE_S));
}

export function clearSessionCookies(response: NextResponse): void {
  response.cookies.set(ACCESS_COOKIE, "", cookieOptions(0));
  response.cookies.set(REFRESH_COOKIE, "", cookieOptions(0));
}

/** En-têtes utiles à l'audit côté API (adresse et agent du client), jamais les cookies. */
export function forwardedHeaders(request: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  const forwardedFor = request.headers.get("x-forwarded-for");
  const userAgent = request.headers.get("user-agent");
  const language = request.headers.get("accept-language");
  const requestId = request.headers.get("x-request-id");
  if (forwardedFor) headers["X-Forwarded-For"] = forwardedFor;
  if (userAgent) headers["User-Agent"] = userAgent.slice(0, 512);
  if (language) headers["Accept-Language"] = language.slice(0, 256);
  if (requestId && /^[A-Za-z0-9-]{1,64}$/.test(requestId)) headers["X-Request-ID"] = requestId;
  return headers;
}

/** Appel JSON à l'API avec délai ; renvoie le statut et le corps décodé (ou null s'il est illisible). */
export async function callApi(
  path: string,
  init: { method: string; body?: unknown; headers?: Record<string, string>; timeoutMs?: number },
): Promise<{ status: number; payload: unknown }> {
  const response = await upstreamFetch(`${upstreamBase()}${path}`, {
    method: init.method,
    headers: { Accept: "application/json", "Content-Type": "application/json", ...init.headers },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
    cache: "no-store",
    signal: AbortSignal.timeout(init.timeoutMs ?? 15_000),
  });
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  return { status: response.status, payload };
}

export function envelopeData(payload: unknown): unknown {
  return typeof payload === "object" && payload !== null ? (payload as { data?: unknown }).data : undefined;
}

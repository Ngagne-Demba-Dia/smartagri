import { NextResponse, type NextRequest } from "next/server";

import { checkCsrf, envelopeError, forwardedHeaders } from "@/lib/server/bff";
import { upstreamBase, upstreamFetch } from "@/lib/server/upstream";
import { ACCESS_COOKIE } from "@/lib/session-cookies";

export const dynamic = "force-dynamic";

/**
 * Proxy BFF vers l'API v1. Le navigateur appelle /api/v1/…, le BFF ajoute « Authorization: Bearer »
 * à partir du cookie httpOnly. Garde-fous :
 * - segments de chemin restreints (pas de « .. », pas d'encodage exotique) ;
 * - /v1/auth/* passe par les routes dédiées, /v1/telemetry/* est réservé aux kits et au téléphone relais ;
 * - requêtes mutantes : X-Requested-With + Origin (checkCsrf), corps JSON limité à 256 Kio ;
 * - Set-Cookie de l'API jamais relayé.
 */
const SEGMENT = /^[A-Za-z0-9_~-][A-Za-z0-9._~-]{0,127}$/;
const BLOCKED_ROOTS = new Set(["auth", "telemetry"]);
const MAX_BODY_BYTES = 256 * 1024;
const DEFAULT_TIMEOUT_MS = 20_000;
const SLOW_TIMEOUT_MS = 60_000; // assistant (appel du modèle côté API) et exports
const RELAYED_RESPONSE_HEADERS = ["content-type", "content-disposition", "retry-after", "x-request-id"];

type Params = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, { params }: Params): Promise<NextResponse> {
  const { path } = await params;
  const root = path[0] ?? "";
  if (path.length === 0 || BLOCKED_ROOTS.has(root) || !path.every((s) => SEGMENT.test(s) && s !== "." && s !== "..")) {
    return envelopeError("NOT_FOUND", "Ressource introuvable.", 404);
  }

  const method = request.method.toUpperCase();
  const mutating = method !== "GET" && method !== "HEAD";
  if (mutating) {
    const rejected = checkCsrf(request);
    if (rejected) return rejected;
  }

  const accessToken = request.cookies.get(ACCESS_COOKIE)?.value;
  if (!accessToken) return envelopeError("UNAUTHENTICATED", "Authentification requise.", 401);

  let body: string | undefined;
  if (mutating) {
    const declared = Number(request.headers.get("content-length") ?? "0");
    if (declared > MAX_BODY_BYTES) return envelopeError("PAYLOAD_TOO_LARGE", "Requête trop volumineuse.", 413);
    body = await request.text();
    if (Buffer.byteLength(body, "utf8") > MAX_BODY_BYTES) return envelopeError("PAYLOAD_TOO_LARGE", "Requête trop volumineuse.", 413);
    if (body && !(request.headers.get("content-type") ?? "").startsWith("application/json")) {
      return envelopeError("VALIDATION_ERROR", "Corps JSON attendu.", 415);
    }
  }

  const target = `${upstreamBase()}/v1/${path.join("/")}${request.nextUrl.search}`;
  const slow = root === "assistant" || path.join("/").endsWith(".csv");

  let upstream: Response;
  try {
    upstream = await upstreamFetch(target, {
      method,
      headers: {
        Accept: request.headers.get("accept") ?? "application/json",
        Authorization: `Bearer ${accessToken}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
        ...forwardedHeaders(request),
      },
      body: body || undefined,
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(slow ? SLOW_TIMEOUT_MS : DEFAULT_TIMEOUT_MS),
    });
  } catch {
    return envelopeError("UPSTREAM_UNAVAILABLE", "Service indisponible. Réessayez dans un instant.", 503);
  }

  if (upstream.status >= 300 && upstream.status < 400) {
    return envelopeError("BAD_RESPONSE", "Réponse inattendue du serveur.", 502);
  }

  const headers = new Headers({ "Cache-Control": "no-store" });
  for (const name of RELAYED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new NextResponse(upstream.body, { status: upstream.status, headers });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;

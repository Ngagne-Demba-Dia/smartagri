import type { NextRequest } from "next/server";

import {
  callApi,
  checkCsrf,
  envelopeData,
  envelopeError,
  envelopeOk,
  forwardedHeaders,
  isTokenPair,
  setSessionCookies,
} from "@/lib/server/bff";

export const dynamic = "force-dynamic";

const MAX_BODY_BYTES = 4_096;

/** Connexion par e-mail ou téléphone : les jetons restent dans des cookies httpOnly, jamais renvoyés au client. */
export async function POST(request: NextRequest) {
  const rejected = checkCsrf(request);
  if (rejected) return rejected;

  const raw = await request.text();
  if (Buffer.byteLength(raw, "utf8") > MAX_BODY_BYTES) return envelopeError("PAYLOAD_TOO_LARGE", "Requête trop volumineuse.", 413);

  let body: unknown;
  try {
    body = JSON.parse(raw);
  } catch {
    return envelopeError("VALIDATION_ERROR", "Corps JSON invalide.", 400);
  }
  const { username, password } = (body ?? {}) as Record<string, unknown>;
  if (
    typeof username !== "string" ||
    typeof password !== "string" ||
    username.trim().length < 3 ||
    username.length > 254 ||
    password.length < 1 ||
    password.length > 256
  ) {
    return envelopeError("VALIDATION_ERROR", "Identifiant ou mot de passe manquant.", 400);
  }

  try {
    const { status, payload } = await callApi("/v1/auth/token", {
      method: "POST",
      body: { username: username.trim(), password },
      headers: forwardedHeaders(request),
    });
    const pair = envelopeData(payload);
    if (status !== 200 || !isTokenPair(pair)) {
      if (status === 429) return envelopeError("RATE_LIMITED", "Trop de tentatives. Réessayez plus tard.", 429);
      return envelopeError("INVALID_CREDENTIALS", "Identifiant ou mot de passe incorrect.", 401);
    }
    const response = envelopeOk({ expires_in: pair.expires_in });
    setSessionCookies(response, pair);
    return response;
  } catch {
    return envelopeError("UPSTREAM_UNAVAILABLE", "Service indisponible. Réessayez dans un instant.", 503);
  }
}

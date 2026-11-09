import type { NextRequest } from "next/server";

import {
  callApi,
  checkCsrf,
  clearSessionCookies,
  envelopeData,
  envelopeError,
  envelopeOk,
  forwardedHeaders,
  isTokenPair,
  setSessionCookies,
} from "@/lib/server/bff";
import { REFRESH_COOKIE } from "@/lib/session-cookies";

export const dynamic = "force-dynamic";

/** Rotation du jeton de rafraîchissement (l'API révoque la famille en cas de réutilisation). */
export async function POST(request: NextRequest) {
  const rejected = checkCsrf(request);
  if (rejected) return rejected;

  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) return envelopeError("UNAUTHENTICATED", "Session expirée.", 401);

  try {
    const { status, payload } = await callApi("/v1/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      headers: forwardedHeaders(request),
    });
    const pair = envelopeData(payload);
    if (status !== 200 || !isTokenPair(pair)) {
      const response = envelopeError("UNAUTHENTICATED", "Session expirée.", 401);
      clearSessionCookies(response);
      return response;
    }
    const response = envelopeOk({ expires_in: pair.expires_in });
    setSessionCookies(response, pair);
    return response;
  } catch {
    return envelopeError("UPSTREAM_UNAVAILABLE", "Service indisponible.", 503);
  }
}

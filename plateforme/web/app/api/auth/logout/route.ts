import type { NextRequest } from "next/server";

import { callApi, checkCsrf, clearSessionCookies, envelopeOk, forwardedHeaders } from "@/lib/server/bff";
import { REFRESH_COOKIE } from "@/lib/session-cookies";

export const dynamic = "force-dynamic";

const LOGOUT_TIMEOUT_MS = 5_000;

/**
 * Déconnexion : révoque le jeton de rafraîchissement côté API puis efface les cookies.
 * Les cookies sont effacés même si l'API est injoignable : la session locale ne doit jamais survivre au clic.
 */
export async function POST(request: NextRequest) {
  const rejected = checkCsrf(request);
  if (rejected) return rejected;

  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  let revoked = false;
  if (refreshToken) {
    try {
      // POST /v1/auth/logout {refresh_token} révoque toute la famille du jeton (rejouable sans erreur).
      const { status } = await callApi("/v1/auth/logout", {
        method: "POST",
        body: { refresh_token: refreshToken },
        headers: forwardedHeaders(request),
        timeoutMs: LOGOUT_TIMEOUT_MS,
      });
      revoked = status >= 200 && status < 300;
    } catch {
      revoked = false;
    }
  }

  const response = envelopeOk({ logged_out: true, revoked });
  clearSessionCookies(response);
  return response;
}

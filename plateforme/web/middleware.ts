import { NextResponse, type NextRequest } from "next/server";

import { LOCALE_COOKIE, LOCALE_HEADER, isLocale, negotiateLocale } from "@/i18n/routing";
import { buildCsp, createNonce } from "@/lib/csp";
import { ACCESS_COOKIE, REFRESH_COOKIE } from "@/lib/session-cookies";

/** Pages accessibles sans session (chemin sans le préfixe de langue). */
const PUBLIC_PATHS = new Set(["/login"]);
const HOME_PATH = "/tableau";

/**
 * Middleware des pages : langue, session, CSP à nonce.
 * - Toute URL est préfixée par la langue (/fr, /wo, /ff) ; sinon redirection vers la langue négociée.
 * - Sans cookie de session, redirection vers /{langue}/login?next=… (la validité du jeton est vérifiée
 *   par l'API à chaque appel ; ici on ne fait qu'orienter la navigation).
 * - La CSP porte un nonce neuf par requête, transmis à Next.js par l'en-tête de requête.
 * Les routes /api/* ne passent pas ici (voir `config.matcher`) : elles se protègent elles-mêmes.
 */
export function middleware(request: NextRequest): NextResponse {
  const { pathname, search } = request.nextUrl;
  const [, first = "", ...rest] = pathname.split("/");

  if (!isLocale(first)) {
    const cookieLocale = request.cookies.get(LOCALE_COOKIE)?.value;
    const locale = isLocale(cookieLocale) ? cookieLocale : negotiateLocale(request.headers.get("accept-language"));
    const target = pathname === "/" ? HOME_PATH : pathname;
    return NextResponse.redirect(new URL(`/${locale}${target}${search}`, request.url));
  }

  const locale = first;
  const innerPath = `/${rest.join("/")}`.replace(/\/+$/, "") || "/";
  const hasSession = request.cookies.has(ACCESS_COOKIE) || request.cookies.has(REFRESH_COOKIE);

  if (innerPath === "/") {
    return NextResponse.redirect(new URL(`/${locale}${HOME_PATH}`, request.url));
  }
  if (!hasSession && !PUBLIC_PATHS.has(innerPath)) {
    const login = new URL(`/${locale}/login`, request.url);
    login.searchParams.set("next", `${innerPath}${search}`);
    return NextResponse.redirect(login);
  }
  if (hasSession && innerPath === "/login") {
    return NextResponse.redirect(new URL(`/${locale}${HOME_PATH}`, request.url));
  }

  const nonce = createNonce();
  const csp = buildCsp(nonce, process.env.NODE_ENV === "development");
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);
  requestHeaders.set(LOCALE_HEADER, locale);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("Cache-Control", "private, no-store");
  response.cookies.set(LOCALE_COOKIE, locale, { path: "/", sameSite: "lax", maxAge: 365 * 24 * 3600 });
  return response;
}

export const config = {
  // Exclut l'API (BFF), les fichiers de build et les fichiers statiques à extension.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|robots.txt|.*\\.[a-zA-Z0-9]+$).*)"],
};

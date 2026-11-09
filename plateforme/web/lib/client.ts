/**
 * Client API unique du navigateur (BFF same-origin). Aucun jeton ici : les cookies httpOnly
 * voyagent seuls ; rien n'est écrit dans localStorage ni sessionStorage.
 */
import { createApiClient } from "./api";
import { LOGIN_SLUG, localeFromPathname, localePath, stripLocale } from "./nav";

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  const { pathname, search } = window.location;
  const locale = localeFromPathname(pathname);
  if (stripLocale(pathname).startsWith(`/${LOGIN_SLUG}`)) return;
  const next = encodeURIComponent(stripLocale(`${pathname}${search}`));
  window.location.assign(`${localePath(locale, `/${LOGIN_SLUG}`)}?next=${next}`);
}

export const api = createApiClient({ baseUrl: "/api", onSessionExpired: redirectToLogin });

/** Segment d'URL sûr pour un identifiant venu de l'API ou de l'URL. */
export const seg = (id: string): string => encodeURIComponent(id);

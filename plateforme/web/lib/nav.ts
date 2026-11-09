/**
 * Chemins internes. `safeNext` empêche toute redirection ouverte après connexion :
 * seul un chemin relatif à l'application est accepté, toujours préfixé par la langue.
 */
import { DEFAULT_LOCALE, isLocale, type Locale } from "@/i18n/routing";

export const HOME_SLUG = "tableau";
export const LOGIN_SLUG = "login";

const CONTROL_CHARS = /[\u0000-\u001f\u007f]/;

export function localePath(locale: Locale, path: string): string {
  return `/${locale}${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * `next` vient de l'URL (?next=…) : il est hostile par défaut.
 * Refusé : vide, absolu (« https: »), protocole relatif (« // »), antislash, caractères de contrôle,
 * retour vers la page de connexion. Le résultat commence toujours par « /{langue}/ ».
 */
export function safeNext(next: string | null | undefined, locale: Locale): string {
  const home = localePath(locale, `/${HOME_SLUG}`);
  if (!next || !next.startsWith("/") || next.startsWith("//")) return home;
  if (next.includes("\\") || CONTROL_CHARS.test(next)) return home;
  const [path = ""] = next.split(/[?#]/);
  const [, first] = path.split("/");
  const prefixed = isLocale(first);
  const inner = prefixed ? stripLocale(path) : path;
  if (inner === `/${LOGIN_SLUG}` || inner.startsWith(`/${LOGIN_SLUG}/`)) return home;
  // Un `next` déjà préfixé par une langue n'est pas préfixé une seconde fois.
  return prefixed ? next : localePath(locale, next);
}

/** Langue lue dans un chemin « /fr/… » ; langue par défaut sinon. */
export function localeFromPathname(pathname: string): Locale {
  const [, first] = pathname.split("/");
  return isLocale(first) ? first : DEFAULT_LOCALE;
}

/** Chemin sans le préfixe de langue (« /fr/parcelles?x=1 » → « /parcelles?x=1 »). */
export function stripLocale(pathWithSearch: string): string {
  const [, first, ...rest] = pathWithSearch.split("/");
  return isLocale(first) ? `/${rest.join("/")}` : pathWithSearch;
}

/** Paramètres de recherche reçus par une page App Router (Next 15 : une promesse). */
export type PageSearchParams = Promise<Record<string, string | string[] | undefined>>;

/** Paramètre de recherche Next.js (string | string[] | undefined) → première valeur non vide, ou null. */
export function firstParam(value: string | readonly string[] | undefined): string | null {
  const first = typeof value === "string" ? value : value?.[0];
  return first ? first : null;
}

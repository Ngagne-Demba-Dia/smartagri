/** Langues de l'interface (CONVENTIONS : fr par défaut, wo et ff via next-intl). */
export const LOCALES = ["fr", "wo", "ff"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "fr";

/** Langues dont les fichiers de messages attendent encore une traduction par un locuteur natif. */
export const UNTRANSLATED_LOCALES: ReadonlySet<Locale> = new Set<Locale>(["wo", "ff"]);

/** Cookie (non sensible) qui mémorise la langue choisie. */
export const LOCALE_COOKIE = "NEXT_LOCALE";

/** En-tête de requête interne posé par middleware.ts, lu par i18n/request.ts. */
export const LOCALE_HEADER = "x-agri-locale";

export function isLocale(value: string | undefined | null): value is Locale {
  return value != null && (LOCALES as readonly string[]).includes(value);
}

/** Choisit une langue d'après Accept-Language (correspondance sur le code principal). */
export function negotiateLocale(acceptLanguage: string | null): Locale {
  if (!acceptLanguage) return DEFAULT_LOCALE;
  const ranked = acceptLanguage
    .split(",")
    .map((part) => {
      const [tag = "", ...params] = part.trim().split(";");
      const q = params.find((p) => p.trim().startsWith("q="));
      return { code: tag.toLowerCase().split("-")[0] ?? "", q: q ? Number(q.split("=")[1]) : 1 };
    })
    .filter((entry) => entry.code && Number.isFinite(entry.q))
    .sort((a, b) => b.q - a.q);
  const match = ranked.find((entry) => isLocale(entry.code));
  return match && isLocale(match.code) ? match.code : DEFAULT_LOCALE;
}

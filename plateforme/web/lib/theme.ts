/**
 * Préférence de thème. Elle vit dans un cookie (jamais dans localStorage, doc 10 §7) pour que le layout
 * serveur pose `data-theme` dès le premier octet : pas de flash clair avant le thème sombre.
 * Sans cookie, c'est la préférence du système (prefers-color-scheme) qui décide.
 */
export const THEME_COOKIE = "sa-theme";
export const THEMES = ["light", "dark"] as const;
export type Theme = (typeof THEMES)[number];

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

export function parseTheme(value: string | null | undefined): Theme | null {
  return THEMES.find((theme) => theme === value) ?? null;
}

export function otherTheme(theme: Theme): Theme {
  return theme === "dark" ? "light" : "dark";
}

/** Valeur à affecter à document.cookie ; SameSite=Lax, sans donnée personnelle. */
export function themeCookie(theme: Theme): string {
  return `${THEME_COOKIE}=${theme}; path=/; max-age=${ONE_YEAR_SECONDS}; SameSite=Lax`;
}

/** Thème effectivement affiché : le choix explicite (data-theme) l'emporte sur la préférence du système. */
export function resolveTheme(attribute: string | null | undefined, systemPrefersDark: boolean): Theme {
  return parseTheme(attribute) ?? (systemPrefersDark ? "dark" : "light");
}

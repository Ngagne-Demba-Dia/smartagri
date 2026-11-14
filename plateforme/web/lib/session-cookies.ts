/**
 * Noms et options des cookies de session du BFF (doc 10 §7).
 * Les jetons de l'API ne quittent jamais le serveur Next.js : ni localStorage, ni JavaScript du navigateur.
 */
export const ACCESS_COOKIE = "sa_at";
export const REFRESH_COOKIE = "sa_rt";

/** Durée de vie du jeton de rafraîchissement (CONVENTIONS §5 : 30 jours). */
export const REFRESH_MAX_AGE_S = 30 * 24 * 3600;

/** Marge retirée à la durée du jeton d'accès pour que le cookie disparaisse avant l'expiration du JWT. */
export const ACCESS_EXPIRY_MARGIN_S = 30;

/** Valeur attendue de l'en-tête X-Requested-With sur les requêtes mutantes vers le BFF. */
export const CSRF_HEADER = "x-requested-with";
export const CSRF_HEADER_VALUE = "smartagri-web";

export interface CookieOptions {
  httpOnly: true;
  secure: boolean;
  sameSite: "strict";
  path: string;
  maxAge: number;
}

/** `secure` n'est désactivé qu'en développement local (http://localhost) ou en banc simulé local (AGRI_MOCK=1). */
export function cookieOptions(maxAge: number, path = "/"): CookieOptions {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV !== "development" && process.env.AGRI_MOCK !== "1",
    sameSite: "strict",
    path,
    maxAge,
  };
}

import { LOGIN_SLUG, stripLocale } from "./nav";

/**
 * « Scène » visuelle d'un écran : la même photo de champ, recadrée et teintée différemment selon la page
 * (CSS `[data-scene="…"]` dans app/globals.css). Purement décoratif : aucune donnée, aucun appel.
 */
export type Scene = "default" | "dashboard" | "parcelles" | "irrigation" | "maladies" | "recommandations" | "login";

const SCENE_BY_SLUG: Readonly<Record<string, Scene>> = {
  tableau: "dashboard",
  parcelles: "parcelles",
  fertilisation: "parcelles",
  vegetation: "parcelles",
  cultures: "parcelles",
  irrigation: "irrigation",
  meteo: "irrigation",
  previsions: "irrigation",
  maladies: "maladies",
  risques: "maladies",
  pieges: "maladies",
  recommandations: "recommandations",
  assistant: "recommandations",
  [LOGIN_SLUG]: "login",
};

/** Scène d'un chemin d'URL (avec ou sans préfixe de langue) ; « default » pour tout écran non listé. */
export function sceneForPath(pathname: string): Scene {
  const first = stripLocale(pathname).split(/[/?#]/).find((part) => part !== "") ?? "";
  return SCENE_BY_SLUG[first] ?? "default";
}

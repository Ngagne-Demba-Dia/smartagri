import { LOGIN_SLUG, stripLocale } from "./nav";

/**
 * « Scène » visuelle d'un écran : photographie agricole de domaine et ambiance chromatique selon la page
 * (CSS `[data-scene="…"]` dans app/globals.css). Purement décoratif : aucune donnée, aucun appel.
 */
export type Scene =
  | "default"
  | "dashboard"
  | "parcelles"
  | "irrigation"
  | "maladies"
  | "recommandations"
  | "kit"
  | "marches"
  | "login";

const SCENE_BY_SLUG: Readonly<Record<string, Scene>> = {
  tableau: "dashboard",
  parcelles: "parcelles",
  exploitations: "parcelles",
  campagnes: "parcelles",
  carte: "parcelles",
  fertilisation: "parcelles",
  vegetation: "parcelles",
  cultures: "parcelles",
  irrigation: "irrigation",
  meteo: "irrigation",
  previsions: "irrigation",
  planning: "irrigation",
  maladies: "maladies",
  risques: "maladies",
  pieges: "maladies",
  recommandations: "recommandations",
  assistant: "recommandations",
  kit: "kit",
  equipements: "kit",
  alertes: "kit",
  marches: "marches",
  rendement: "marches",
  rapports: "marches",
  [LOGIN_SLUG]: "login",
};

const PHOTO_BY_SCENE: Readonly<Record<Scene, string>> = {
  default: "/img/champ-hero.webp",
  dashboard: "/img/champ-hero.webp",
  recommandations: "/img/champ-hero.webp",
  login: "/img/champ-hero.webp",
  irrigation: "/img/irrigation-goutte.webp",
  parcelles: "/img/parcelles-niayes.webp",
  maladies: "/img/phyto-feuille.webp",
  kit: "/img/kit-terrain.webp",
  marches: "/img/recolte-marche.webp",
};

/** Scène d'un chemin d'URL (avec ou sans préfixe de langue) ; « default » pour tout écran non listé. */
export function sceneForPath(pathname: string): Scene {
  const first = stripLocale(pathname).split(/[/?#]/).find((part) => part !== "") ?? "";
  return SCENE_BY_SLUG[first] ?? "default";
}

/** Photographie WebP associée à une scène métier. */
export function photoForScene(scene: Scene): string {
  return PHOTO_BY_SCENE[scene] ?? PHOTO_BY_SCENE.default;
}

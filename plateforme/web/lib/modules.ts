/**
 * Les 13 modules de doc 10 §3.2, leur groupe de navigation (§3.1) et leur version.
 * Les slugs d'URL suivent la maquette (maquettes/index.html) ; doc 10 n'en fixe pas.
 */
import type { IconName } from "@/components/Icon";

export type NavGroup = "pilotage" | "terrain" | "cultures" | "ia" | "materiel";
export type ModuleVersion = "MVP" | "MVP_V2" | "V1_1" | "V2" | "V3";

export interface ModuleDef {
  id: number;
  slug: string;
  key: string;
  group: NavGroup;
  version: ModuleVersion;
  icon: IconName;
  /** Écran complet (les 13 modules le sont dans cette livraison) ; sinon coquille typée (états vide, chargement, erreur). */
  complete: boolean;
}

export const MODULES: readonly ModuleDef[] = [
  {
    id: 1,
    slug: "tableau",
    key: "dashboard",
    group: "pilotage",
    version: "MVP",
    icon: "home",
    complete: true,
  },
  {
    id: 13,
    slug: "rapports",
    key: "reports",
    group: "pilotage",
    version: "MVP",
    icon: "chart",
    complete: true,
  },
  {
    id: 2,
    slug: "exploitations",
    key: "farms",
    group: "terrain",
    version: "MVP",
    icon: "farm",
    complete: true,
  },
  {
    id: 3,
    slug: "parcelles",
    key: "fields",
    group: "terrain",
    version: "MVP",
    icon: "sprout",
    complete: true,
  },
  { id: 4, slug: "carte", key: "map", group: "terrain", version: "MVP", icon: "map", complete: true },
  { id: 5, slug: "meteo", key: "weather", group: "terrain", version: "MVP", icon: "cloud", complete: true },
  { id: 6, slug: "cultures", key: "crops", group: "cultures", version: "MVP", icon: "leaf", complete: true },
  {
    id: 11,
    slug: "campagnes",
    key: "campaigns",
    group: "cultures",
    version: "MVP",
    icon: "calendar",
    complete: true,
  },
  { id: 9, slug: "rendement", key: "yield", group: "cultures", version: "MVP", icon: "trend", complete: true },
  {
    id: 7,
    slug: "recommandations",
    key: "recommendations",
    group: "ia",
    version: "MVP",
    icon: "lightbulb",
    complete: true,
  },
  { id: 8, slug: "maladies", key: "diseases", group: "ia", version: "MVP", icon: "camera", complete: true },
  { id: 12, slug: "assistant", key: "assistant", group: "ia", version: "MVP", icon: "chat", complete: true },
  {
    id: 10,
    slug: "equipements",
    key: "equipment",
    group: "materiel",
    version: "MVP",
    icon: "wrench",
    complete: true,
  },
];

export const NAV_GROUPS: readonly NavGroup[] = ["pilotage", "terrain", "cultures", "ia", "materiel"];

/** Barre du bas sur téléphone (doc 10 §3.1) : Accueil, Carte, Alertes, Assistant, puis « Menu ». */
export const MOBILE_TABS = [
  { slug: "tableau", key: "home", icon: "home" },
  { slug: "carte", key: "map", icon: "map" },
  { slug: "alertes", key: "alerts", icon: "bell" },
  { slug: "assistant", key: "assistant", icon: "chat" },
] as const satisfies readonly { slug: string; key: string; icon: IconName }[];

export function moduleBySlug(slug: string): ModuleDef {
  const found = MODULES.find((m) => m.slug === slug);
  if (!found) throw new Error(`Module inconnu : ${slug}`);
  return found;
}

/**
 * Écrans de service du doc 18 : un écran par service d'IA, hors des 13 modules du doc 10 (MODULES reste inchangé).
 * La barre latérale les affiche dans leur groupe, après les modules.
 */
import type { IconName } from "@/components/Icon";

import type { ModuleVersion, NavGroup } from "./modules";
import type { ModuleTitleKey } from "./server/page-metadata";

export interface ServiceScreenDef {
  /** Numéro du service dans le doc 16 §9.3. */
  service: number;
  slug: string;
  /** Clé du titre dans le namespace « modules ». */
  key: ModuleTitleKey;
  group: NavGroup;
  version: ModuleVersion;
  icon: IconName;
}

export const SERVICE_SCREENS: readonly ServiceScreenDef[] = [
  { service: 3, slug: "irrigation", key: "irrigation", group: "ia", version: "MVP", icon: "drop" },
  { service: 7, slug: "kit", key: "kit", group: "materiel", version: "MVP", icon: "pump" },
  {
    service: 6,
    slug: "fertilisation",
    key: "fertilization",
    group: "cultures",
    version: "MVP",
    icon: "sprout",
  },
  { service: 9, slug: "risques", key: "pestRisk", group: "ia", version: "MVP", icon: "warn" },
  { service: 2, slug: "previsions", key: "soilForecast", group: "ia", version: "MVP", icon: "drops" },
  { service: 4, slug: "planning", key: "irrigationPlan", group: "ia", version: "MVP", icon: "calendar" },
  { service: 10, slug: "pieges", key: "traps", group: "materiel", version: "MVP", icon: "bug" },
  { service: 11, slug: "vegetation", key: "vegetation", group: "cultures", version: "MVP", icon: "satellite" },
  { service: 15, slug: "marches", key: "markets", group: "cultures", version: "MVP", icon: "market" },
];

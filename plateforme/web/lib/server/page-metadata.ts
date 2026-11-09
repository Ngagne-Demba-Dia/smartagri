import "server-only";

import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

/** Clés de titre d'écran (namespace « modules ») : les 13 modules de doc 10 §3.2 et le journal des alertes. */
export type ModuleTitleKey =
  | "dashboard"
  | "reports"
  | "farms"
  | "fields"
  | "map"
  | "weather"
  | "crops"
  | "campaigns"
  | "yield"
  | "recommendations"
  | "diseases"
  | "assistant"
  | "equipment"
  | "alerts"
  | "irrigation"
  | "kit"
  | "fertilization"
  | "pestRisk"
  | "soilForecast"
  | "irrigationPlan"
  | "traps"
  | "vegetation"
  | "markets";

/** Titre d'onglet propre à chaque écran (WCAG 2.4.2), complété par le gabarit « … · SmartAgri92 » du layout racine. */
export async function moduleMetadata(key: ModuleTitleKey): Promise<Metadata> {
  const tm = await getTranslations("modules");
  return { title: tm(key) };
}

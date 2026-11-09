/** Calculs d'affichage de l'écran Risques (doc 18 §6) : le contrat ne dit pas si un organisme est un ravageur ou une maladie. */
import type { PestRisk } from "@/lib/contracts/field";
import { showsAsPercent } from "@/lib/contracts/provenance";

export type PestEntry = PestRisk["pests"][number];
export type PestLevel = PestEntry["level"];
export type PestKind = "pest" | "disease";

const LEVEL_RANK: Record<PestLevel, number> = { low: 0, medium: 1, high: 2 };
const PERCENT = 100;

/** Niveau le plus élevé parmi les organismes suivis ; null s'il n'y en a aucun. Dérivé, pas un score du modèle. */
export function highestLevel(pests: readonly PestEntry[]): PestLevel | null {
  return pests.reduce<PestLevel | null>(
    (best, p) => (best === null || LEVEL_RANK[p.level] > LEVEL_RANK[best] ? p.level : best),
    null,
  );
}

export interface PestGroups {
  pest: PestEntry[];
  disease: PestEntry[];
  unclassified: PestEntry[];
}

/** Répartit les organismes selon le dictionnaire d'affichage ; un code inconnu va dans « non classé ». */
export function groupPests(
  pests: readonly PestEntry[],
  kindOf: (code: string) => PestKind | null,
): PestGroups {
  const groups: PestGroups = { pest: [], disease: [], unclassified: [] };
  for (const entry of pests) {
    const kind = kindOf(entry.pest_code);
    (kind === null ? groups.unclassified : groups[kind]).push(entry);
  }
  return groups;
}

export type ProbabilityView =
  { type: "percent"; value: number } | { type: "uncalibrated" } | { type: "none" };

/** Une probabilité n'est montrée en % que si elle est calibrée (doc 16 §6.3). */
export function probabilityView(p: number | null, calibrated: boolean): ProbabilityView {
  if (p === null) return { type: "none" };
  return showsAsPercent(p, calibrated) ? { type: "percent", value: p * PERCENT } : { type: "uncalibrated" };
}

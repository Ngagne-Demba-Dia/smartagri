/** Calculs d'affichage de l'écran Fertilisation (doc 18 §5) : aucune dose n'est recalculée. */
import type { Fertilization } from "@/lib/contracts/field";
import { provenanceState } from "@/lib/contracts/provenance";

export type Nutrient = "n" | "p" | "k";

export const NUTRIENTS: readonly Nutrient[] = ["n", "p", "k"];

/** Dose en kg/ha d'un élément ; null = pas de dose calculée. */
export function doseOf(result: Fertilization, nutrient: Nutrient): number | null {
  if (nutrient === "n") return result.n_kg_ha;
  if (nutrient === "p") return result.p_kg_ha;
  return result.k_kg_ha;
}

export const hasAnyDose = (result: Fertilization): boolean =>
  NUTRIENTS.some((n) => doseOf(result, n) !== null);

export type ReadingKind = "withDose" | "noDose";

/** « Lecture du résultat » : phrase composée des champs du contrat, jamais un raisonnement du modèle. */
export const readingKind = (result: Fertilization): ReadingKind =>
  hasAnyDose(result) ? "withDose" : "noDose";

/** Vrai si le résultat est périmé ou en valeur de secours. */
export const isDegraded = (result: Fertilization): boolean => provenanceState(result.provenance) !== "fresh";

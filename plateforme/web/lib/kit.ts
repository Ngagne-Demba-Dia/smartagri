/** Calculs d'affichage de l'écran Kit (doc 18 §4) : aucune valeur n'est recalculée, seule la péremption est évaluée. */
import { ApiError } from "@/lib/api";
import { PARAM_VALIDITY_DAYS, type KitParameters, type ParameterBlock } from "@/lib/contracts/device";
import { provenanceState } from "@/lib/contracts/provenance";
import { isBlockExpired } from "@/services/ai/kit-parameters";

export type BlockStatus = "fresh" | "stale" | "fallback" | "expired";

const NOT_FOUND = 404;

/** Durée de validité du bloc, en jours (doc 16 §6.1). */
export const validityDays = (block: ParameterBlock): number => PARAM_VALIDITY_DAYS[block];

/**
 * État d'un bloc : « secours » et « périmé » viennent de la provenance ; « expired » signale un bloc
 * plus vieux que sa durée de validité. Un bloc n'est « fresh » que s'il n'est ni l'un ni l'autre.
 */
export function blockStatus(
  params: KitParameters,
  block: ParameterBlock,
  now: Date = new Date(),
): BlockStatus {
  const provenance = params.provenance[block];
  const state = provenanceState(provenance);
  if (state !== "fresh") return state;
  return isBlockExpired(block, provenance.computed_at, now) ? "expired" : "fresh";
}

/** Le jeu n'a pas été publié pour ce kit : état vide, pas une erreur (doc 18 §4). */
export const isNotPublished = (error: unknown): boolean =>
  error instanceof ApiError && error.status === NOT_FOUND;

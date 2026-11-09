/**
 * Bascule des simulations de doc 16 §9.5. Module neutre (ni « server-only » ni msw) : le BFF, les mocks
 * et les tests l'importent sans charger le serveur simulé.
 *
 * AGRI_MOCK=1 fait répondre le BFF par les gestionnaires MSW de mocks/ au lieu de l'API réelle.
 * Désactivé par défaut ; chaque simulation disparaît quand sa route réelle est livrée (doc 17 §3).
 */

/** Hôte réservé (RFC 6761 : « .invalid » ne se résout jamais) : une fuite vers le réseau échoue. */
export const MOCK_BASE = "http://api.mock.invalid";

export function isMockMode(): boolean {
  return process.env.AGRI_MOCK === "1";
}

/**
 * Scénarios de doc 16 §9.5 (nominal, périmé, repli, abstention, erreur 503, vide). Ici plutôt que dans mocks/ :
 * le panneau de pilotage du navigateur les lit sans embarquer les simulations.
 */
export const MOCK_SCENARIOS = ["nominal", "stale", "fallback", "abstention", "error_503", "empty"] as const;
export type MockScenario = (typeof MOCK_SCENARIOS)[number];

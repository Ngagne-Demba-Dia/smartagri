/**
 * Point d'entrée des simulations (doc 16 §9.5). Le BFF l'importe dynamiquement quand AGRI_MOCK=1 ;
 * les tests l'importent directement. Une route non simulée répond 404 : jamais d'appel réseau.
 */
import { getResponse } from "msw";

import { fail } from "./base";
import { aiHandlers } from "./handlers/ai";
import { coreHandlers } from "./handlers/core";

export const handlers = [...coreHandlers, ...aiHandlers];

export async function handleMock(request: Request): Promise<Response> {
  const response = await getResponse(handlers, request);
  return response ?? fail("NOT_FOUND", "Route non simulée.", 404);
}

export { MOCK_SCENARIOS, resetScenarios, setScenario, snapshot, type MockScenario } from "./scenario";
export { resetStore } from "./store";

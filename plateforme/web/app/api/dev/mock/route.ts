import type { NextRequest } from "next/server";
import { z } from "zod";

import { SERVICE_IDS } from "@/lib/contracts/registry";
import { MOCK_SCENARIOS, isMockMode } from "@/lib/mock-config";
import { allServiceModes, defaultMode } from "@/lib/service-mode";
import { checkCsrf, envelopeError, envelopeOk } from "@/lib/server/bff";
import { ACCESS_COOKIE } from "@/lib/session-cookies";
import { principalFromRequest } from "@/mocks/auth";
import { latencyFactor } from "@/mocks/base";
import {
  clearScenario,
  resetScenarios,
  setScenario,
  snapshot,
  type ScenarioSnapshot,
} from "@/mocks/scenario";

export const dynamic = "force-dynamic";

/**
 * Pilotage des simulations (doc 16 §9.5), en mode simulé seulement (AGRI_MOCK=1) ; sinon 404, comme une
 * route qui n'existe pas. Session simulée exigée ; requêtes mutantes protégées par checkCsrf.
 * - GET : scénario global, surcharges par service, listes des scénarios et des services, facteur de latence ;
 * - POST {scenario, service?} : change le scénario global ou celui d'un service ; scenario null avec un
 *   service retire sa surcharge (il suit de nouveau le global) ;
 * - DELETE : revient au nominal partout et vide l'état modifiable (seuils, acquittements, retours).
 */
const MAX_BODY_CHARS = 1_024;

const ChangeSchema = z.strictObject({
  scenario: z.enum(MOCK_SCENARIOS).nullable(),
  service: z.enum(SERVICE_IDS).optional(),
});

/** latencyFactor : facteur AGRI_MOCK_LATENCY appliqué aux latences de la table des services (0 : aucune attente). */
const view = (current: ScenarioSnapshot) => ({
  ...current,
  scenarios: MOCK_SCENARIOS,
  services: SERVICE_IDS,
  latencyFactor: latencyFactor(),
  defaultMode: defaultMode(),
  serviceModes: allServiceModes(),
});

/** Garde commune : mode simulé, puis session simulée valide (jeton du cookie httpOnly). */
function guard(request: NextRequest) {
  if (!isMockMode()) return envelopeError("NOT_FOUND", "Ressource introuvable.", 404);
  const token = request.cookies.get(ACCESS_COOKIE)?.value;
  const principal = token
    ? principalFromRequest(new Request(request.url, { headers: { authorization: `Bearer ${token}` } }))
    : null;
  return principal ? null : envelopeError("UNAUTHENTICATED", "Authentification requise.", 401);
}

export function GET(request: NextRequest) {
  return guard(request) ?? envelopeOk(view(snapshot()));
}

export async function POST(request: NextRequest) {
  const rejected = guard(request) ?? checkCsrf(request);
  if (rejected) return rejected;
  const text = await request.text();
  if (text.length > MAX_BODY_CHARS) return envelopeError("PAYLOAD_TOO_LARGE", "Requête trop volumineuse.", 413);
  let body: unknown;
  try {
    body = JSON.parse(text) as unknown;
  } catch {
    return envelopeError("VALIDATION_ERROR", "Corps JSON attendu.", 422);
  }
  const parsed = ChangeSchema.safeParse(body);
  if (!parsed.success) return envelopeError("VALIDATION_ERROR", "Scénario ou service inconnu.", 422);
  const { scenario, service } = parsed.data;
  if (scenario !== null) return envelopeOk(view(setScenario(scenario, service)));
  if (!service) return envelopeError("VALIDATION_ERROR", "Service attendu pour retirer une surcharge.", 422);
  return envelopeOk(view(clearScenario(service)));
}

export async function DELETE(request: NextRequest) {
  const rejected = guard(request) ?? checkCsrf(request);
  if (rejected) return rejected;
  const { resetStore } = await import("@/mocks/store");
  resetStore();
  return envelopeOk(view(resetScenarios()));
}

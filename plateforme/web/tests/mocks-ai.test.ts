/**
 * Tests de contrat des 18 services d'IA simulés (doc 16 §9.3–9.5) : chaque scénario de chaque service
 * produit une enveloppe conforme au schéma du registre, avec la provenance attendue (§9.2).
 */
import { beforeEach, describe, expect, it } from "vitest";

import { envelopeSchema } from "@/lib/contracts/envelope";
import { provenanceState } from "@/lib/contracts/provenance";
import { SERVICE_IDS, serviceById, type ServiceId } from "@/lib/contracts/registry";
import { MOCK_SCENARIOS, resetScenarios, resetStore, setScenario, type MockScenario } from "@/mocks";

import { SERVICE_CALLS, call, provenances, readEnvelope } from "./helpers";

process.env.AGRI_MOCK_LATENCY = "0";

/** Services intégrés à une route existante : en error_503, la route répond 200 et seul le bloc vaut null. */
const RESOLVES_ON_503: ReadonlySet<ServiceId> = new Set(["water_savings"]);
const UNAVAILABLE_CODE: Partial<Record<ServiceId, string>> = {
  weather: "WEATHER_UNAVAILABLE",
  assistant_chat: "ASSISTANT_UNAVAILABLE",
  assistant_transcribe: "ASSISTANT_UNAVAILABLE",
};
/** Réponses d'erreur prévues par le contrat pour un scénario « vide ». */
const EMPTY_ERRORS: Partial<Record<ServiceId, { status: number; code: string }>> = {
  kit_parameters: { status: 404, code: "NOT_FOUND" },
  yield_forecast: { status: 404, code: "NO_ACTIVE_CYCLE" },
};
/** Le diagnostic garde sa probabilité en repli et en abstention : elle explique pourquoi le modèle s'abstient. */
const KEEPS_CONFIDENCE: ReadonlySet<ServiceId> = new Set(["disease_diagnosis"]);

beforeEach(() => {
  resetScenarios();
  resetStore();
});

function expectProvenance(service: ServiceId, scenario: MockScenario, data: unknown): void {
  const blocks = provenances(data);
  if (scenario === "nominal") expect(blocks.length).toBeGreaterThan(0);
  for (const block of blocks) {
    if (scenario === "stale") {
      expect(block.stale).toBe(true);
      expect(Date.parse(block.computed_at)).toBeLessThan(Date.now() - 3 * 3_600_000 + 1_000);
    } else if (scenario === "fallback") {
      expect(provenanceState(block)).toBe("fallback");
    } else {
      expect(provenanceState(block)).toBe("fresh");
    }
    if ((scenario === "fallback" || scenario === "abstention") && !KEEPS_CONFIDENCE.has(service)) {
      expect(block.confidence.kind).toBe("none");
    }
  }
}

describe.each(SERVICE_IDS)("service %s", (service) => {
  const definition = serviceById(service);

  it.each(MOCK_SCENARIOS)("scénario %s conforme au contrat", async (scenario) => {
    setScenario(scenario, service);
    const response = await call(SERVICE_CALLS[service]);
    const body = await readEnvelope(response);
    expect(body.meta?.mock).toBe(true);
    expect(body.meta?.scenario).toBe(scenario);

    if (scenario === "error_503" && !RESOLVES_ON_503.has(service)) {
      expect(response.status).toBe(503);
      expect(response.headers.get("Retry-After")).toBe("30");
      expect(body.success).toBe(false);
      expect(body.error?.code).toBe(UNAVAILABLE_CODE[service] ?? "MODEL_UNAVAILABLE");
      return;
    }
    const expectedError = scenario === "empty" ? EMPTY_ERRORS[service] : undefined;
    if (expectedError) {
      expect(response.status).toBe(expectedError.status);
      expect(body.error?.code).toBe(expectedError.code);
      return;
    }
    expect(response.status).toBe(200);
    const parsed = envelopeSchema(definition.schema).safeParse(body);
    expect(parsed.success, JSON.stringify(parsed.error?.issues.slice(0, 3))).toBe(true);
    expect(body.success).toBe(true);
    expect(body.error).toBeNull();
    expectProvenance(service, scenario, body.data);
  });

  it("suit le scénario global quand il n'a pas de surcharge", async () => {
    setScenario("stale");
    const body = await readEnvelope(await call(SERVICE_CALLS[service]));
    expect(body.meta?.scenario).toBe("stale");
  });
});

describe("règles transverses des services", () => {
  it("refuse une requête sans jeton (401) avant toute simulation", async () => {
    const response = await call(SERVICE_CALLS.weather, null);
    expect(response.status).toBe(401);
    expect((await readEnvelope(response)).error?.code).toBe("UNAUTHENTICATED");
  });

  it("répond 404 sur une route non simulée, sans appel réseau", async () => {
    const response = await call({ method: "GET", path: "/v1/inconnue" });
    expect(response.status).toBe(404);
    expect((await readEnvelope(response)).error?.code).toBe("NOT_FOUND");
  });

  it("cache une parcelle hors du périmètre de l'utilisateur (404)", async () => {
    const response = await call(SERVICE_CALLS.weather, "farmer");
    expect(response.status).toBe(404);
  });

  it("water_savings en error_503 : route 200, bloc d'économie d'eau absent", async () => {
    setScenario("error_503", "water_savings");
    const response = await call(SERVICE_CALLS.water_savings);
    expect(response.status).toBe(200);
    expect(provenances((await readEnvelope(response)).data)).toHaveLength(0);
  });

  it("le repli utilise un modèle de secours, jamais le modèle nominal présenté comme frais", async () => {
    setScenario("fallback");
    const blocks = provenances((await readEnvelope(await call(SERVICE_CALLS.irrigation_need))).data);
    expect(blocks.map((b) => [b.model_name, b.fallback_step, b.source])).toContainEqual([
      "irr_water_balance",
      2,
      "rules",
    ]);
  });
});

/**
 * Règles propres à certaines routes d'IA simulées (doc 16 §9.3–9.5) : retours sur recommandation,
 * alertes et acquittement, quotas et limites de l'assistant, rattachement des photos, validation des
 * paramètres de requête. Les rôles suivent lib/roles.ts ; hors périmètre, la réponse est 404.
 */
import { beforeEach, describe, expect, it } from "vitest";

import { UPLOAD_MAX_BYTES } from "@/lib/contracts/assistant";
import { AlertListSchema } from "@/lib/contracts/device";
import { RecommendationListSchema } from "@/lib/contracts/field";
import { IrrigationPlanSchema, MapLayersSchema, PriceForecastSchema } from "@/lib/contracts/org";
import { resetScenarios, resetStore, setScenario } from "@/mocks";
import { CHAT_LIMIT, feedbackCounts } from "@/mocks/store";

import { call, diagnosisBody, get, post, readEnvelope, transcribeBody, type Role } from "./helpers";

process.env.AGRI_MOCK_LATENCY = "0";

beforeEach(() => {
  resetScenarios();
  resetStore();
});

async function expectError(
  response: Response,
  status: number,
  code: string,
): Promise<Record<string, unknown> | undefined> {
  const body = await readEnvelope(response);
  expect(response.status).toBe(status);
  expect(body.success).toBe(false);
  expect(body.error?.code).toBe(code);
  return body.error?.details;
}

async function recommendationIds(role: Role = "admin"): Promise<string[]> {
  const body = await readEnvelope(await call(get("/v1/fields/fld-mboro-1/recommendations"), role));
  return RecommendationListSchema.parse(body.data).map((r) => r.id);
}

describe("POST /v1/recommendations/:id/feedback", () => {
  it("enregistre le retour d'un rôle autorisé et renvoie la recommandation", async () => {
    const [recoId] = await recommendationIds();
    expect(recoId).toBe("rec-fld-mboro-1-irr");
    const response = await call(
      post(`/v1/recommendations/${recoId}/feedback`, { feedback: "followed" }),
      "coop_manager",
    );
    expect(response.status).toBe(200);
    expect(((await readEnvelope(response)).data as { id: string }).id).toBe(recoId);
    expect(feedbackCounts().followed).toBe(1);
  });

  it("refuse l'agronome (403), qui conseille sans valider l'application", async () => {
    await expectError(
      await call(
        post("/v1/recommendations/rec-fld-mboro-1-irr/feedback", { feedback: "ignored" }),
        "agronomist",
      ),
      403,
      "FORBIDDEN",
    );
    expect(feedbackCounts().ignored).toBe(0);
  });

  it("répond 404 sur une recommandation inconnue ou hors périmètre", async () => {
    await expectError(
      await call(post("/v1/recommendations/rec-inconnue/feedback", { feedback: "followed" })),
      404,
      "NOT_FOUND",
    );
    await expectError(
      await call(
        post("/v1/recommendations/rec-fld-mboro-1-irr/feedback", { feedback: "followed" }),
        "farmer",
      ),
      404,
      "NOT_FOUND",
    );
  });

  it("refuse une valeur de retour hors liste (422) en rappelant les valeurs admises", async () => {
    const details = await expectError(
      await call(post("/v1/recommendations/rec-fld-mboro-1-irr/feedback", { feedback: "peut-être" })),
      422,
      "VALIDATION_ERROR",
    );
    expect(details?.allowed).toEqual(["followed", "partially_followed", "ignored", "not_applicable"]);
  });

  it("garde l'identifiant stable d'un scénario à l'autre", async () => {
    setScenario("fallback", "recommendations");
    expect(await recommendationIds()).toContain("rec-fld-mboro-1-irr");
  });
});

describe("GET /v1/alerts et POST /v1/alerts/:id/ack", () => {
  it("filtre par statut, limite le nombre et trie du plus récent au plus ancien", async () => {
    const body = await readEnvelope(await call(get("/v1/alerts?status=open&limit=2")));
    const alerts = AlertListSchema.parse(body.data);
    expect(alerts).toHaveLength(2);
    expect(alerts.every((a) => a.status === "open")).toBe(true);
    expect(alerts[0]?.created_at.localeCompare(alerts[1]?.created_at ?? "")).toBeGreaterThan(0);
  });

  it("ne montre que les alertes de l'organisation de l'utilisateur", async () => {
    const alerts = AlertListSchema.parse((await readEnvelope(await call(get("/v1/alerts"), "farmer"))).data);
    expect(alerts.map((a) => a.id)).toEqual(["alt-0005"]);
  });

  it.each(["status=fermee", "limit=0", "limit=501", "limit=abc"])("refuse ?%s (422)", async (query) => {
    await expectError(await call(get(`/v1/alerts?${query}`)), 422, "VALIDATION_ERROR");
  });

  it("acquitte une alerte ouverte pour tout rôle de l'organisation", async () => {
    const response = await call(post("/v1/alerts/alt-0001/ack"), "agronomist");
    const alert = AlertListSchema.element.parse((await readEnvelope(response)).data);
    expect(alert.status).toBe("acknowledged");
    expect(alert.acknowledged_at).not.toBeNull();
    const open = AlertListSchema.parse((await readEnvelope(await call(get("/v1/alerts?status=open")))).data);
    expect(open.map((a) => a.id)).not.toContain("alt-0001");
  });

  it("laisse inchangée une alerte déjà résolue", async () => {
    const alert = AlertListSchema.element.parse(
      (await readEnvelope(await call(post("/v1/alerts/alt-0006/ack")))).data,
    );
    expect(alert.status).toBe("resolved");
  });

  it("répond 404 sur une alerte inconnue ou d'une autre organisation", async () => {
    await expectError(await call(post("/v1/alerts/alt-9999/ack")), 404, "NOT_FOUND");
    await expectError(await call(post("/v1/alerts/alt-0001/ack"), "farmer"), 404, "NOT_FOUND");
  });

  it("sert les alertes sans provenance quand le service de santé est indisponible", async () => {
    setScenario("error_503", "device_health");
    const response = await call(get("/v1/alerts"));
    expect(response.status).toBe(200);
    const alerts = AlertListSchema.parse((await readEnvelope(response)).data);
    expect(alerts.length).toBeGreaterThan(0);
    expect(alerts.every((a) => a.provenance === null)).toBe(true);
  });
});

describe("POST /v1/assistant/chat", () => {
  const message = { message: "Faut-il arroser ce soir ?" };

  it(`limite à ${CHAT_LIMIT} messages par minute et indique quand réessayer (429)`, async () => {
    for (let i = 0; i < CHAT_LIMIT; i += 1) {
      expect((await call(post("/v1/assistant/chat", message), "farmer")).status).toBe(200);
    }
    const response = await call(post("/v1/assistant/chat", message), "farmer");
    await expectError(response, 429, "RATE_LIMITED");
    expect(Number(response.headers.get("Retry-After"))).toBeGreaterThanOrEqual(1);
    expect((await call(post("/v1/assistant/chat", message), "coop_manager")).status).toBe(200);
  });

  it.each([{ message: "   " }, { message: "x".repeat(2001) }, {}])(
    "refuse un message vide ou trop long (422)",
    async (body) => {
      await expectError(await call(post("/v1/assistant/chat", body)), 422, "MESSAGE_INVALID");
    },
  );

  it("refuse un corps de plus de 256 Kio (413) en donnant la limite", async () => {
    const details = await expectError(
      await call(post("/v1/assistant/chat", { message: "x".repeat(UPLOAD_MAX_BYTES) })),
      413,
      "PAYLOAD_TOO_LARGE",
    );
    expect(details?.max_bytes).toBe(UPLOAD_MAX_BYTES);
  });
});

describe("diagnostic des maladies (photos)", () => {
  it("POST /v1/diagnoses enregistre le diagnostic (201) avec un identifiant simulé", async () => {
    const response = await call(post("/v1/diagnoses", diagnosisBody()));
    expect(response.status).toBe(201);
    const data = (await readEnvelope(response)).data as { id: string; label: string };
    expect(data.id).toBe(`diag-mock-${data.label}-1`);
    const second = (await readEnvelope(await call(post("/v1/diagnoses", diagnosisBody(null, "dev-0001")))))
      .data as { id: string };
    expect(second.id).toMatch(/-2$/);
  });

  it("/analyze n'enregistre rien : l'identifiant reste null", async () => {
    const data = (await readEnvelope(await call(post("/v1/diagnoses/analyze", diagnosisBody())))).data as {
      id: unknown;
    };
    expect(data.id).toBeNull();
  });

  it("exige une parcelle ou un kit (422)", async () => {
    await expectError(
      await call(post("/v1/diagnoses/analyze", diagnosisBody(null, null))),
      422,
      "VALIDATION_ERROR",
    );
  });

  it("refuse un format d'image non pris en charge (422)", async () => {
    await expectError(
      await call(post("/v1/diagnoses", { ...diagnosisBody(), content_type: "image/gif" })),
      422,
      "VALIDATION_ERROR",
    );
  });

  it("répond 404 pour une parcelle ou un kit hors périmètre", async () => {
    await expectError(await call(post("/v1/diagnoses/analyze", diagnosisBody()), "farmer"), 404, "NOT_FOUND");
    await expectError(
      await call(post("/v1/diagnoses/analyze", diagnosisBody(null, "dev-0001")), "farmer"),
      404,
      "NOT_FOUND",
    );
  });

  it("refuse une photo de plus de 256 Kio (413)", async () => {
    const body = { ...diagnosisBody(), image_base64: "A".repeat(UPLOAD_MAX_BYTES) };
    await expectError(await call(post("/v1/diagnoses/analyze", body)), 413, "PAYLOAD_TOO_LARGE");
  });
});

describe("POST /v1/assistant/transcribe", () => {
  it.each([0, -1, 61])("refuse une durée de %s s (422)", async (duration) => {
    await expectError(
      await call(post("/v1/assistant/transcribe", { ...transcribeBody(), duration_s: duration })),
      422,
      "VALIDATION_ERROR",
    );
  });

  it("refuse un type de contenu qui n'est pas audio (422)", async () => {
    await expectError(
      await call(post("/v1/assistant/transcribe", { ...transcribeBody(), content_type: "video/mp4" })),
      422,
      "VALIDATION_ERROR",
    );
  });

  it("refuse un enregistrement trop volumineux (413)", async () => {
    const body = { ...transcribeBody(), audio_base64: "A".repeat(UPLOAD_MAX_BYTES) };
    await expectError(await call(post("/v1/assistant/transcribe", body)), 413, "PAYLOAD_TOO_LARGE");
  });
});

describe("GET /v1/farms/:id/map", () => {
  it("ne sert que les couches demandées, avec une provenance par couche", async () => {
    const map = MapLayersSchema.parse(
      (await readEnvelope(await call(get("/v1/farms/farm-mboro/map?layers=crop_type")))).data,
    );
    expect(Object.keys(map.layers)).toEqual(["crop_type"]);
    expect(map.features.some((f) => f.properties.kind === "boundary")).toBe(false);
  });

  it("sert les trois couches par défaut", async () => {
    const map = MapLayersSchema.parse((await readEnvelope(await call(get("/v1/farms/farm-mboro/map")))).data);
    expect(Object.keys(map.layers).sort()).toEqual(["crop_type", "field_boundary", "salinity"]);
  });

  it("refuse une couche inconnue (422) et une exploitation hors périmètre (404)", async () => {
    await expectError(
      await call(get("/v1/farms/farm-mboro/map?layers=crop_type,relief")),
      422,
      "VALIDATION_ERROR",
    );
    await expectError(await call(get("/v1/farms/farm-mboro/map"), "farmer"), 404, "NOT_FOUND");
  });
});

describe("GET /v1/markets/prices", () => {
  it.each(["crop=oignon", "market=Thiaroye", "crop=%20&market=Thiaroye"])(
    "exige crop et market (422) : ?%s",
    async (query) => {
      await expectError(await call(get(`/v1/markets/prices?${query}`)), 422, "VALIDATION_ERROR");
    },
  );

  it("répond 404 sur une culture sans prévision, en listant les cultures couvertes", async () => {
    const details = await expectError(
      await call(get("/v1/markets/prices?crop=mil&market=Thiaroye")),
      404,
      "NOT_FOUND",
    );
    expect(details?.crops).toContain("oignon");
  });

  it("ignore la casse de la culture", async () => {
    const forecast = PriceForecastSchema.parse(
      (await readEnvelope(await call(get("/v1/markets/prices?crop=OIGNON&market=Thiaroye")))).data,
    );
    expect(forecast.crop).toBe("oignon");
    expect(forecast.horizons).toHaveLength(4);
  });

  it.each(["empty", "abstention"] as const)("scénario %s : aucun horizon de prévision", async (scenario) => {
    setScenario(scenario, "price_forecast");
    const forecast = PriceForecastSchema.parse(
      (await readEnvelope(await call(get("/v1/markets/prices?crop=oignon&market=Thiaroye")))).data,
    );
    expect(forecast.horizons).toEqual([]);
  });
});

describe("validation des paramètres de requête", () => {
  it.each([
    ["météo : days hors bornes", "/v1/fields/fld-mboro-1/weather?days=17"],
    ["météo : days non entier", "/v1/fields/fld-mboro-1/weather?days=2.5"],
    ["sol : horizon nul", "/v1/fields/fld-mboro-1/soil-forecast?horizons=0,24"],
    ["sol : horizon au-delà de 168 h", "/v1/fields/fld-mboro-1/soil-forecast?horizons=24,200"],
    ["sol : plus de six horizons", "/v1/fields/fld-mboro-1/soil-forecast?horizons=1,2,3,4,5,6,7"],
    ["sol : horizon non numérique", "/v1/fields/fld-mboro-1/soil-forecast?horizons=24,abc"],
    ["végétation : from après to", "/v1/fields/fld-mboro-1/vegetation?from=2026-11-05&to=2026-11-01"],
    ["végétation : date illisible", "/v1/fields/fld-mboro-1/vegetation?to=demain"],
    ["végétation : from illisible", "/v1/fields/fld-mboro-1/vegetation?from=hier"],
    ["végétation : fenêtre trop longue", "/v1/fields/fld-mboro-1/vegetation?from=2020-01-01&to=2026-11-01"],
    ["pièges : fenêtre trop longue", "/v1/devices/dev-0001/trap-counts?from=2020-01-01&to=2026-11-01"],
    ["rapport : périmètre inconnu", "/v1/reports/kpis?scope=region"],
    ["rapport : exploitation sans scope_id", "/v1/reports/kpis?scope=farm"],
    ["rapport : fenêtre de plus de 400 jours", "/v1/reports/kpis?from=2024-01-01&to=2026-11-01"],
    ["plan : date illisible", "/v1/farms/farm-mboro/irrigation-plan?date=bientot"],
  ])("%s → 422", async (_label, path) => {
    await expectError(await call(get(path)), 422, "VALIDATION_ERROR");
  });

  it.each([
    "/v1/reports/kpis?scope=farm&scope_id=farm-ndiol",
    "/v1/reports/kpis?scope=field&scope_id=fld-ndiol-1",
    "/v1/reports/kpis?scope=org&scope_id=org-demo-ndiol",
    "/v1/fields/fld-inconnue/weather",
    "/v1/devices/dev-0101/health",
    "/v1/farms/farm-ndiol/irrigation-plan",
  ])("hors périmètre de la coopérative → 404 : %s", async (path) => {
    await expectError(await call(get(path), "coop_manager"), 404, "NOT_FOUND");
  });

  it("rapport par parcelle et par exploitation dans le périmètre", async () => {
    for (const query of ["scope=field&scope_id=fld-mboro-1", "scope=farm&scope_id=farm-mboro", "scope=org"]) {
      expect((await call(get(`/v1/reports/kpis?${query}`), "coop_manager")).status).toBe(200);
    }
  });

  it("plan d'irrigation : commence le jour demandé, créneaux enchaînés sans chevauchement par pompe", async () => {
    const plan = IrrigationPlanSchema.parse(
      (await readEnvelope(await call(get("/v1/farms/farm-mboro/irrigation-plan?date=2026-11-12")))).data,
    );
    expect(plan.date).toBe("2026-11-12");
    expect(plan.slots[0]?.start).toBe("2026-11-12T06:00:00Z");
    plan.slots.slice(1).forEach((slot, i) => {
      const previous = plan.slots[i];
      if (previous?.pump_id === slot.pump_id) expect(slot.start).toBe(previous.end);
    });
  });
});

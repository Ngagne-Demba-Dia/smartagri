/**
 * Contrats front de doc 16 §9 (baseline v1) : règles d'affichage de la provenance et de la confiance,
 * validation par contrat et registre des 18 services. Les tests lisent la baseline, ils ne la modifient pas.
 */
import { describe, expect, it } from "vitest";
import { z } from "zod";

import { ApiError } from "@/lib/api";
import {
  AI_ERROR_STATUS,
  ALERTS_SCHEMA,
  AlertListSchema,
  ConfidenceSchema,
  MAX_FALLBACK_STEP,
  OptionalProvenance,
  ProvenanceSchema,
  SERVICES,
  SERVICE_IDS,
  VISION_ABSTAIN_BELOW,
  confidenceView,
  envelopeSchema,
  parseContract,
  provenanceState,
  serviceById,
  showsAsPercent,
  type Confidence,
  type Provenance,
  type ServiceId,
} from "@/lib/contracts";

const NONE: Confidence = { kind: "none", value: null, p10: null, p90: null, calibrated: false };

const provenance = (overrides: Partial<Provenance> = {}): Provenance => ({
  model_name: "irr_need_24h",
  model_version: "3",
  source: "agriml",
  fallback_step: 0,
  computed_at: "2026-11-09T06:00:00Z",
  data_as_of: "2026-11-09T05:00:00Z",
  stale: false,
  confidence: NONE,
  ...overrides,
});

describe("provenanceState", () => {
  it("fresh, stale puis fallback, le repli l'emportant sur la péremption", () => {
    expect(provenanceState(provenance())).toBe("fresh");
    expect(provenanceState(provenance({ stale: true }))).toBe("stale");
    expect(provenanceState(provenance({ fallback_step: 1 }))).toBe("fallback");
    expect(provenanceState(provenance({ fallback_step: 2, stale: true }))).toBe("fallback");
  });
});

describe("confidenceView", () => {
  it("kind none : rien à afficher", () => {
    expect(confidenceView(NONE)).toEqual({ type: "none" });
  });

  it("intervalle : p10–p90 et calibration ; bornes manquantes → rien", () => {
    expect(confidenceView({ kind: "interval", value: null, p10: 4.1, p90: 7.9, calibrated: false })).toEqual({
      type: "interval",
      p10: 4.1,
      p90: 7.9,
      calibrated: false,
    });
    expect(confidenceView({ kind: "interval", value: null, p10: 4.1, p90: null, calibrated: true })).toEqual({
      type: "none",
    });
  });

  it("probabilité non calibrée : jamais un pourcentage", () => {
    expect(
      confidenceView({ kind: "probability", value: 0.94, p10: null, p90: null, calibrated: false }),
    ).toEqual({
      type: "uncalibrated",
    });
  });

  it("probabilité calibrée : pourcentage ; valeur absente → rien", () => {
    expect(
      confidenceView({ kind: "class_probability", value: 0.82, p10: null, p90: null, calibrated: true }),
    ).toEqual({
      type: "percent",
      value: 0.82,
    });
    expect(
      confidenceView({ kind: "probability", value: null, p10: null, p90: null, calibrated: true }),
    ).toEqual({ type: "none" });
  });
});

describe("ConfidenceSchema et ProvenanceSchema", () => {
  it("complète p10 et p90 absents par null", () => {
    expect(ConfidenceSchema.parse({ kind: "probability", value: 0.5, calibrated: true })).toEqual({
      kind: "probability",
      value: 0.5,
      p10: null,
      p90: null,
      calibrated: true,
    });
  });

  it.each([
    ["none avec une valeur", { kind: "none", value: 0.4, calibrated: false }],
    ["none avec un intervalle", { kind: "none", value: null, p10: 1, p90: 2, calibrated: false }],
    ["interval sans p90", { kind: "interval", value: null, p10: 1, calibrated: true }],
    ["interval inversé", { kind: "interval", value: null, p10: 3, p90: 2, calibrated: true }],
    ["probabilité hors [0, 1]", { kind: "probability", value: 1.2, calibrated: true }],
  ])("refuse %s", (_label, value) => {
    expect(ConfidenceSchema.safeParse(value).success).toBe(false);
  });

  it("borne fallback_step à MAX_FALLBACK_STEP et exige des dates ISO avec fuseau", () => {
    expect(MAX_FALLBACK_STEP).toBe(2);
    expect(ProvenanceSchema.safeParse(provenance({ fallback_step: 2 })).success).toBe(true);
    expect(ProvenanceSchema.safeParse(provenance({ fallback_step: 3 })).success).toBe(false);
    expect(ProvenanceSchema.safeParse(provenance({ computed_at: "2026-11-09 06:00" })).success).toBe(false);
    expect(ProvenanceSchema.safeParse({ ...provenance(), source: "openai" }).success).toBe(false);
  });

  it("OptionalProvenance vaut null quand une route existante ne l'envoie pas encore", () => {
    expect(OptionalProvenance.parse(undefined)).toBeNull();
  });
});

describe("showsAsPercent et seuil d'abstention", () => {
  it("pourcentage seulement si calibré et dans [0, 1]", () => {
    expect(showsAsPercent(0.8, true)).toBe(true);
    expect(showsAsPercent(0.8, false)).toBe(false);
    expect(showsAsPercent(null, true)).toBe(false);
    expect(showsAsPercent(1.5, true)).toBe(false);
    expect(showsAsPercent(-0.1, true)).toBe(false);
  });

  it("la vision s'abstient sous 0,7 (doc 16 §9.4 n° 8)", () => {
    expect(VISION_ABSTAIN_BELOW).toBe(0.7);
  });
});

describe("parseContract et envelopeSchema", () => {
  const schema = z.object({ n: z.number() });

  it("renvoie la donnée validée", () => {
    expect(parseContract(schema, { n: 1 }, "weather")).toEqual({ n: 1 });
  });

  it("lève BAD_RESPONSE 502 avec le service et au plus 5 écarts", () => {
    const wide = z.object(Object.fromEntries(Array.from({ length: 8 }, (_, i) => [`k${i}`, z.number()])));
    try {
      parseContract(wide, {}, "vegetation");
      expect.unreachable();
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const error = e as ApiError;
      expect([error.code, error.status, error.details?.service]).toEqual(["BAD_RESPONSE", 502, "vegetation"]);
      expect(error.details?.issues).toHaveLength(5);
    }
  });

  it("nomme la racine quand la donnée entière est fausse", () => {
    try {
      parseContract(schema, "texte", "weather");
      expect.unreachable();
    } catch (e) {
      expect(String((e as ApiError).details?.issues)).toContain("(racine)");
    }
  });

  it("envelopeSchema accepte data null et une méta simulée", () => {
    const envelope = envelopeSchema(schema);
    expect(
      envelope.safeParse({
        success: false,
        data: null,
        error: { code: "X", message: "" },
        meta: { mock: true },
      }).success,
    ).toBe(true);
    expect(envelope.safeParse({ success: true, data: { n: "1" }, error: null, meta: null }).success).toBe(
      false,
    );
  });

  it("AI_ERROR_STATUS associe chaque code d'IA à son statut HTTP", () => {
    expect(AI_ERROR_STATUS.MODEL_UNAVAILABLE).toBe(503);
    expect(AI_ERROR_STATUS.PAYLOAD_TOO_LARGE).toBe(413);
    expect(AI_ERROR_STATUS.NO_ACTIVE_CYCLE).toBe(404);
  });
});

describe("registre des 18 services (doc 16 §9.3)", () => {
  it("18 identifiants uniques, numérotés de 1 à 18 dans l'ordre", () => {
    expect(SERVICE_IDS).toHaveLength(18);
    expect(new Set(SERVICE_IDS).size).toBe(18);
    expect(SERVICES.map((s) => s.number)).toEqual(Array.from({ length: 18 }, (_, i) => i + 1));
    expect(SERVICES.map((s) => s.id)).toEqual([...SERVICE_IDS]);
  });

  it("chaque service a au moins une route, un modèle, un module et une latence simulée positive", () => {
    for (const service of SERVICES) {
      expect(service.routes.length).toBeGreaterThan(0);
      expect(service.models.length).toBeGreaterThan(0);
      expect(service.modules.length).toBeGreaterThan(0);
      expect(service.availability.length).toBeGreaterThan(0);
      expect(service.mockLatencyMs).toBeGreaterThan(0);
      expect(service.staleMs).toBeGreaterThanOrEqual(0);
    }
  });

  it("les services interactifs ne sont jamais mis en cache", () => {
    const interactive: ServiceId[] = ["disease_diagnosis", "assistant_chat", "assistant_transcribe"];
    for (const id of interactive) expect(serviceById(id).staleMs).toBe(0);
  });

  it("serviceById lève sur un identifiant inconnu", () => {
    expect(serviceById("weather").number).toBe(1);
    expect(() => serviceById("meteo" as ServiceId)).toThrow("Service inconnu");
  });

  it("les alertes sont validées par leur propre schéma", () => {
    expect(ALERTS_SCHEMA).toBe(AlertListSchema);
  });
});

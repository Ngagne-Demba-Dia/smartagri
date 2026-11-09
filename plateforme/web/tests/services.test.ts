/**
 * Couche services/ai (doc 16 §9.3) : chaque fonction fetchX appelle la bonne route avec le client du front,
 * valide la réponse par son contrat et remonte les erreurs typées. Les simulations MSW servent de serveur.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { ZodError } from "zod";

import { ApiError, createApiClient } from "@/lib/api";
import { UPLOAD_MAX_RAW_BYTES } from "@/lib/contracts/assistant";
import { PARAM_VALIDITY_DAYS } from "@/lib/contracts/device";
import { SERVICE_IDS, serviceById } from "@/lib/contracts/registry";
import { MOCK_BASE } from "@/lib/mock-config";
import { resetScenarios, resetStore, setScenario } from "@/mocks";
import {
  ackAlert,
  aiKeys,
  analyzeDiagnosis,
  base64Bytes,
  exportCsvUrl,
  fetchAlerts,
  fetchDeviceHealth,
  fetchFarmMap,
  fetchFertilization,
  fetchIrrigationNeed,
  fetchIrrigationPlan,
  fetchKitParameters,
  fetchKpis,
  fetchPestRisk,
  fetchPriceForecast,
  fetchRecommendations,
  fetchSoilForecast,
  fetchTrapCounts,
  fetchVegetation,
  fetchWeather,
  fetchYieldForecast,
  isBlockExpired,
  seg,
  sendChat,
  sendRecommendationFeedback,
  staleFor,
  transcribeAudio,
  type FeedbackValue,
} from "@/services/ai";

import { diagnosisBody, mockClient, transcribeBody } from "./helpers";

process.env.AGRI_MOCK_LATENCY = "0";

const DAY_MS = 86_400_000;
const WINDOW = { from: "2026-10-01", to: "2026-11-01" };

beforeEach(() => {
  resetScenarios();
  resetStore();
});

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  const error: unknown = await promise.then(
    () => null,
    (e: unknown) => e,
  );
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

describe("services de parcelle", () => {
  const client = mockClient();

  it("fetchWeather renvoie la prévision du nombre de jours demandé", async () => {
    const weather = await fetchWeather("fld-mboro-1", 3, { client });
    expect(weather.field_id).toBe("fld-mboro-1");
    expect(weather.days).toHaveLength(3);
  });

  it("fetchWeather prend 7 jours par défaut", async () => {
    expect((await fetchWeather("fld-mboro-1", undefined, { client })).days).toHaveLength(7);
  });

  it("fetchSoilForecast, fetchIrrigationNeed, fetchFertilization et fetchPestRisk portent une provenance", async () => {
    const results = await Promise.all([
      fetchSoilForecast("fld-mboro-1", { client }),
      fetchIrrigationNeed("fld-mboro-1", { client }),
      fetchFertilization("fld-mboro-1", { client }),
      fetchPestRisk("fld-mboro-1", { client }),
    ]);
    for (const result of results) expect(result.provenance.model_name.length).toBeGreaterThan(0);
  });

  it("fetchVegetation et fetchYieldForecast suivent la parcelle demandée", async () => {
    const [vegetation, yieldForecast] = await Promise.all([
      fetchVegetation("fld-mboro-1", WINDOW.from, WINDOW.to, { client }),
      fetchYieldForecast("fld-mboro-1", { client }),
    ]);
    expect(vegetation.field_id).toBe("fld-mboro-1");
    expect(yieldForecast.field_id).toBe("fld-mboro-1");
  });

  it("fetchRecommendations liste les recommandations de la parcelle", async () => {
    const list = await fetchRecommendations("fld-mboro-1", { client });
    expect(list.length).toBeGreaterThan(0);
    expect(list.map((r) => r.id)).toContain("rec-fld-mboro-1-irr");
    expect(new Set(list.map((r) => r.kind))).toEqual(new Set(["irrigation", "fertilization"]));
  });

  it("sendRecommendationFeedback renvoie la recommandation", async () => {
    const reco = await sendRecommendationFeedback("rec-fld-mboro-1-irr", "followed", {
      client: mockClient("coop_manager"),
    });
    expect(reco.id).toBe("rec-fld-mboro-1-irr");
  });

  it("sendRecommendationFeedback refuse une valeur hors contrat avant tout appel", () => {
    expect(() =>
      sendRecommendationFeedback("rec-fld-mboro-1-irr", "peut-être" as FeedbackValue, { client }),
    ).toThrow(ZodError);
  });
});

describe("services d'exploitation et d'organisation", () => {
  const client = mockClient();

  it("fetchIrrigationPlan renvoie le plan de l'exploitation à la date demandée", async () => {
    const plan = await fetchIrrigationPlan("farm-mboro", "2026-11-12", { client });
    expect(plan.farm_id).toBe("farm-mboro");
    expect(plan.date).toBe("2026-11-12");
  });

  it("fetchKpis porte le bloc d'économie d'eau ; exportCsvUrl vise le BFF", async () => {
    const kpis = await fetchKpis(WINDOW, { client });
    expect(kpis.kpis.water_savings).not.toBeNull();
    expect(exportCsvUrl(WINDOW)).toBe("/api/v1/reports/export.csv?scope=org&from=2026-10-01&to=2026-11-01");
  });

  it("fetchPriceForecast renvoie la culture et le marché demandés", async () => {
    const prices = await fetchPriceForecast("oignon", "Thiaroye", { client });
    expect(prices.crop).toBe("oignon");
    expect(prices.market).toBe("Thiaroye");
  });

  it("fetchFarmMap sans couche : la simulation sert toutes les couches", async () => {
    const map = await fetchFarmMap("farm-mboro", [], { client });
    expect(new Set(map.features.map((f) => f.properties.kind))).toEqual(
      new Set(["field", "device", "boundary"]),
    );
    expect(Object.keys(map.layers).sort()).toEqual(["crop_type", "field_boundary", "salinity"]);
  });

  it("fetchFarmMap avec couches : seulement les couches demandées", async () => {
    const map = await fetchFarmMap("farm-mboro", ["crop_type"], { client });
    expect(Object.keys(map.layers)).toEqual(["crop_type"]);
    expect(map.features.some((f) => f.properties.kind === "boundary")).toBe(false);
  });
});

describe("services de kit", () => {
  const client = mockClient();

  it("fetchKitParameters et fetchDeviceHealth suivent le kit demandé", async () => {
    const [parameters, health] = await Promise.all([
      fetchKitParameters("dev-0001", { client }),
      fetchDeviceHealth("dev-0001", { client }),
    ]);
    expect(parameters.device_id).toBe("dev-0001");
    expect(health.device_id).toBe("dev-0001");
  });

  it("fetchTrapCounts renvoie les comptages du kit", async () => {
    const counts = await fetchTrapCounts("dev-0001", "2026-11-01T00:00:00Z", "2026-11-09T00:00:00Z", {
      client,
    });
    expect(counts.device_id).toBe("dev-0001");
  });

  it("fetchAlerts filtre par statut ; « all » n'envoie pas de filtre", async () => {
    const open = await fetchAlerts("open", { client });
    const all = await fetchAlerts("all", { client });
    expect(open.every((a) => a.status === "open")).toBe(true);
    expect(new Set(all.map((a) => a.status))).toEqual(new Set(["open", "acknowledged", "resolved"]));
    expect((await fetchAlerts(undefined, { client })).length).toBe(open.length);
  });

  it("ackAlert acquitte l'alerte", async () => {
    const alert = await ackAlert("alt-0001", { client });
    expect(alert.status).toBe("acknowledged");
  });

  it("isBlockExpired applique la durée de validité de chaque bloc (doc 16 §6.1)", () => {
    const now = new Date("2026-11-09T12:00:00Z");
    const daysAgo = (days: number) => new Date(now.getTime() - days * DAY_MS).toISOString();
    expect(isBlockExpired("seuils", daysAgo(PARAM_VALIDITY_DAYS.seuils), now)).toBe(false);
    expect(isBlockExpired("seuils", daysAgo(PARAM_VALIDITY_DAYS.seuils + 0.01), now)).toBe(true);
    expect(isBlockExpired("etalonnage", daysAgo(90), now)).toBe(false);
    expect(isBlockExpired("npk", daysAgo(31), now)).toBe(true);
    expect(isBlockExpired("agro", new Date().toISOString())).toBe(false);
  });
});

describe("assistant et vision", () => {
  const client = mockClient();

  it("sendChat renvoie une réponse et un identifiant de conversation", async () => {
    const reply = await sendChat({ message: "  Quand arroser mes oignons ?  " }, { client });
    expect(reply.conversation_id.length).toBeGreaterThan(0);
    expect(reply.reply.length).toBeGreaterThan(0);
  });

  it("sendChat refuse un message vide avant tout appel", () => {
    expect(() => sendChat({ message: "   " }, { client })).toThrow(ZodError);
  });

  it("transcribeAudio renvoie le texte dans la langue indiquée", async () => {
    const transcription = await transcribeAudio(transcribeBody("wo"), { client });
    expect(transcription.language).toBe("wo");
  });

  it("analyzeDiagnosis renvoie un verdict avec provenance", async () => {
    const diagnosis = await analyzeDiagnosis(diagnosisBody(), { client });
    expect(["healthy", "suspect", "sick"]).toContain(diagnosis.label);
    expect(diagnosis.provenance.model_name.length).toBeGreaterThan(0);
  });

  it("analyzeDiagnosis rejette une image trop lourde (413) sans appel réseau", async () => {
    const fail = createApiClient({
      baseUrl: MOCK_BASE,
      fetchImpl: () => Promise.reject(new Error("aucun appel attendu")),
    });
    const body = { ...diagnosisBody(), image_base64: "A".repeat(270_000) };
    const error = await rejection(analyzeDiagnosis(body, { client: fail }));
    expect([error.code, error.status]).toEqual(["PAYLOAD_TOO_LARGE", 413]);
  });

  it("base64Bytes compte le remplissage", () => {
    expect(base64Bytes("QUJD")).toBe(3);
    expect(base64Bytes("QUI=")).toBe(2);
    expect(base64Bytes("QQ==")).toBe(1);
    expect(base64Bytes("A".repeat(270_000))).toBeGreaterThan(UPLOAD_MAX_RAW_BYTES);
  });
});

describe("erreurs remontées par la couche services", () => {
  it("une réponse non conforme au contrat devient BAD_RESPONSE 502 avec le service en cause", async () => {
    const client = createApiClient({
      baseUrl: MOCK_BASE,
      fetchImpl: () =>
        Promise.resolve(
          Response.json({ success: true, data: { foo: 1 }, error: null, meta: null }, { status: 200 }),
        ),
    });
    const error = await rejection(fetchWeather("fld-mboro-1", 3, { client }));
    expect([error.code, error.status]).toEqual(["BAD_RESPONSE", 502]);
    expect(error.details?.service).toBe("weather");
    expect(Array.isArray(error.details?.issues)).toBe(true);
  });

  it("error_503 sur la météo devient WEATHER_UNAVAILABLE 503", async () => {
    setScenario("error_503", "weather");
    const error = await rejection(fetchWeather("fld-mboro-1", 3, { client: mockClient() }));
    expect([error.code, error.status]).toEqual(["WEATHER_UNAVAILABLE", 503]);
  });

  it("une parcelle hors périmètre devient NOT_FOUND 404", async () => {
    const error = await rejection(fetchIrrigationNeed("fld-mboro-1", { client: mockClient("farmer") }));
    expect([error.code, error.status]).toEqual(["NOT_FOUND", 404]);
  });
});

describe("outils de la couche services", () => {
  it("seg encode un identifiant pour l'URL", () => {
    expect(seg("fld/../x y")).toBe("fld%2F..%2Fx%20y");
  });

  it("staleFor lit la fraîcheur du registre pour chaque service", () => {
    for (const id of SERVICE_IDS) expect(staleFor(id)).toBe(serviceById(id).staleMs);
  });

  it("aiKeys partagent le préfixe de l'objet métier", () => {
    expect(aiKeys.weather("f1", 3)).toEqual(["fields", "f1", "weather", { days: 3 }]);
    expect(aiKeys.irrigationPlan("farm", "2026-11-12")[0]).toBe("farms");
    expect(aiKeys.trapCounts("d1", "a", "b")).toEqual([
      "devices",
      "d1",
      "trap-counts",
      { from: "a", to: "b" },
    ]);
    expect(aiKeys.mapLayers("farm", "")).toEqual(["farms", "farm", "map", { layers: "" }]);
    const prefixes = [
      aiKeys.soilForecast("f"),
      aiKeys.irrigationNeed("f"),
      aiKeys.recommendations("f"),
      aiKeys.fertilization("f"),
      aiKeys.pestRisk("f"),
      aiKeys.vegetation("f", "a", "b"),
      aiKeys.yieldForecast("f"),
    ].map((key) => key[0]);
    expect(new Set(prefixes)).toEqual(new Set(["fields"]));
    expect([aiKeys.kitParameters("d")[0], aiKeys.deviceHealth("d")[0]]).toEqual(["devices", "devices"]);
    expect([aiKeys.alerts("open")[0], aiKeys.kpis("a", "b")[0], aiKeys.prices("c", "m")[0]]).toEqual([
      "alerts",
      "reports",
      "markets",
    ]);
  });
});

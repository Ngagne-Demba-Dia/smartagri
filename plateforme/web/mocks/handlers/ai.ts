/**
 * Gestionnaires MSW des 18 services d'IA (doc 16 §9). Chaque route passe par aiRoute : latence du
 * registre, scénario courant du service, 503 propre au service (sauf `unavailable: "resolve"`).
 * Les réponses portent meta.scenario pour que l'interface et les tests sachent ce qui a été simulé.
 */
import type { HttpHandler } from "msw";

import { ChatInputSchema, DiagnosisInputSchema, TranscribeInputSchema, type DiagnosisInput } from "@/lib/contracts/assistant";
import { FEEDBACK_VALUES, FeedbackInputSchema } from "@/lib/contracts/field";
import { MAP_LAYERS, type MapLayer } from "@/lib/contracts/org";
import { canAckAlerts, canGiveFeedback } from "@/lib/roles";

import { visibleDevice, visibleDeviceSeeds, visibleFarm, visibleField } from "../access";
import type { Principal } from "../auth";
import { fail, notFound, ok, readJson } from "../base";
import { chatReply, diagnosis, transcription } from "../builders/assistant";
import {
  TRAP_DEFAULT_DAYS,
  TRAP_MAX_DAYS,
  alertSeedById,
  alertView,
  alertsView,
  deviceHealth,
  kitParameters,
  trapCounts,
  type AlertFilter,
} from "../builders/device";
import {
  DEFAULT_SOIL_HORIZONS,
  VEGETATION_DEFAULT_DAYS,
  VEGETATION_MAX_DAYS,
  fertilization,
  fieldIdOfRecommendation,
  irrigationNeed,
  pestRisk,
  recommendations,
  soilForecast,
  vegetation,
  weather,
  yieldForecast,
} from "../builders/field";
import { PRICE_CROPS, irrigationPlan, kpiReport, mapLayers, priceForecast } from "../builders/org";
import type { FieldSeed } from "../fixtures/places";
import { aiRoute, dateParam, forbidden, intParam, invalid, type AiContext } from "../route";
import type { MockScenario } from "../scenario";
import { acknowledgeAlert, recordChat, recordDiagnosis, recordFeedback } from "../store";

import { readBoundedJson, reportRequest, tooLarge, windowParams } from "./params";

const WEATHER_DEFAULT_DAYS = 7;
const WEATHER_MAX_DAYS = 16;
const SOIL_MAX_HORIZON_H = 168;
const SOIL_MAX_HORIZONS = 6;
const ALERTS_DEFAULT_LIMIT = 50;
const ALERTS_MAX_LIMIT = 500;
const ALERT_FILTERS: readonly AlertFilter[] = ["open", "acknowledged", "resolved", "all"];

const answer = <T>(data: T, scenario: MockScenario, status = 200): Response => ok(data, { scenario }, status);

/** Route GET /v1/fields/:id/… : 404 hors périmètre, sinon le constructeur du service. */
function fieldRoute(
  service: Parameters<typeof aiRoute>[0],
  path: string,
  build: (seed: FieldSeed, ctx: AiContext) => Response,
): HttpHandler {
  return aiRoute(service, "get", path, (ctx) => {
    const seed = visibleField(ctx.user, ctx.params.id ?? "");
    return seed ? build(seed, ctx) : notFound(ctx.scenario);
  });
}

/* ---------- Services rattachés à une parcelle (1, 2, 3, 5, 6, 9, 11, 12) ---------- */

function parseHorizons(raw: string | null): number[] | null {
  if (raw === null || raw === "") return [...DEFAULT_SOIL_HORIZONS];
  const parts = raw.split(",");
  if (parts.length > SOIL_MAX_HORIZONS || !parts.every((p) => /^\d+$/.test(p))) return null;
  const values = parts.map((p) => Number.parseInt(p, 10));
  return values.every((h) => h >= 1 && h <= SOIL_MAX_HORIZON_H) ? values : null;
}

const fieldHandlers: HttpHandler[] = [
  fieldRoute("weather", "/v1/fields/:id/weather", (seed, { query, scenario, now }) => {
    const days = intParam(query, "days", WEATHER_DEFAULT_DAYS, 1, WEATHER_MAX_DAYS);
    if (days === null) return invalid(`« days » entre 1 et ${WEATHER_MAX_DAYS}.`);
    return answer(weather(seed, days, scenario, now), scenario);
  }),
  fieldRoute("soil_forecast", "/v1/fields/:id/soil-forecast", (seed, { query, scenario, now }) => {
    const horizons = parseHorizons(query.get("horizons"));
    if (!horizons) return invalid(`« horizons » : entiers de 1 à ${SOIL_MAX_HORIZON_H} h séparés par des virgules.`);
    return answer(soilForecast(seed, horizons, scenario, now), scenario);
  }),
  fieldRoute("irrigation_need", "/v1/fields/:id/irrigation-need", (seed, { scenario, now }) =>
    answer(irrigationNeed(seed, scenario, now), scenario),
  ),
  fieldRoute("recommendations", "/v1/fields/:id/recommendations", (seed, { scenario, now }) =>
    answer(recommendations(seed, scenario, now), scenario),
  ),
  fieldRoute("fertilization", "/v1/fields/:id/fertilization", (seed, { scenario, now }) =>
    answer(fertilization(seed, scenario, now), scenario),
  ),
  fieldRoute("pest_risk", "/v1/fields/:id/pest-risk", (seed, { scenario, now }) => answer(pestRisk(seed, scenario, now), scenario)),
  fieldRoute("vegetation", "/v1/fields/:id/vegetation", (seed, { query, scenario, now }) => {
    const window = windowParams(query, now, VEGETATION_DEFAULT_DAYS, VEGETATION_MAX_DAYS);
    if (window instanceof Response) return window;
    return answer(vegetation(seed, window.from, window.to, scenario, now), scenario);
  }),
  fieldRoute("yield_forecast", "/v1/fields/:id/yield-forecast", (seed, { scenario, now }) => {
    const forecast = yieldForecast(seed, scenario, now);
    return forecast
      ? answer(forecast, scenario)
      : fail("NO_ACTIVE_CYCLE", "Aucun cycle cultural en cours sur cette parcelle.", 404, { scenario });
  }),
];

/* ---------- Retour sur une recommandation (service 5) ---------- */

const feedbackHandler = aiRoute("recommendations", "post", "/v1/recommendations/:id/feedback", async (ctx) => {
  const { request, user, params, scenario, now } = ctx;
  const recoId = params.id ?? "";
  const fieldId = fieldIdOfRecommendation(recoId);
  const seed = fieldId ? visibleField(user, fieldId) : null;
  const reco = seed ? recommendations(seed, scenario, now).find((r) => r.id === recoId) : undefined;
  if (!seed || !reco) return notFound(scenario);
  if (!canGiveFeedback(user.me, seed.orgId)) return forbidden();
  const parsed = FeedbackInputSchema.safeParse(await readJson(request));
  if (!parsed.success) return invalid("Retour inconnu.", { allowed: FEEDBACK_VALUES });
  recordFeedback(reco.id, parsed.data.feedback);
  return answer(reco, scenario);
});

/* ---------- Services rattachés à une exploitation (4, 18) ---------- */

function parseLayers(raw: string | null): Set<MapLayer> | null {
  if (raw === null || raw === "") return new Set(MAP_LAYERS);
  const names = raw.split(",");
  const known = (name: string): name is MapLayer => (MAP_LAYERS as readonly string[]).includes(name);
  return names.every(known) ? new Set(names) : null;
}

const farmHandlers: HttpHandler[] = [
  aiRoute("irrigation_plan", "get", "/v1/farms/:id/irrigation-plan", ({ user, params, query, scenario, now }) => {
    const farm = visibleFarm(user, params.id ?? "");
    if (!farm) return notFound(scenario);
    const date = query.has("date") ? dateParam(query, "date") : now;
    if (!date) return invalid("« date » illisible (AAAA-MM-JJ).");
    return answer(irrigationPlan(farm, date, scenario, now), scenario);
  }),
  aiRoute("map_layers", "get", "/v1/farms/:id/map", ({ user, params, query, scenario, now }) => {
    const farm = visibleFarm(user, params.id ?? "");
    if (!farm) return notFound(scenario);
    const layers = parseLayers(query.get("layers"));
    if (!layers) return invalid("Couche inconnue.", { allowed: MAP_LAYERS });
    return answer(mapLayers(farm, layers, scenario, now), scenario);
  }),
];

/* ---------- Kits : paramètres, pièges, santé et alertes (7, 10, 13) ---------- */

const deviceHandlers: HttpHandler[] = [
  aiRoute("kit_parameters", "get", "/v1/devices/:id/parameters", ({ user, params, scenario, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    if (!seed) return notFound(scenario);
    const parameters = kitParameters(seed, scenario, now);
    return parameters
      ? answer(parameters, scenario)
      : fail("NOT_FOUND", "Aucun jeu de paramètres publié pour ce kit.", 404, { scenario });
  }),
  aiRoute("kit_parameters", "post", "/v1/devices/:id/parameters/ack", ({ user, params, scenario, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    if (!seed) return notFound(scenario);
    const parameters = kitParameters(seed, scenario, now);
    return parameters
      ? answer({ ...parameters, applied: true }, scenario)
      : fail("NOT_FOUND", "Aucun jeu de paramètres publié pour ce kit.", 404, { scenario });
  }),
  aiRoute("trap_counts", "get", "/v1/devices/:id/trap-counts", ({ user, params, query, scenario, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    if (!seed) return notFound(scenario);
    const window = windowParams(query, now, TRAP_DEFAULT_DAYS, TRAP_MAX_DAYS);
    if (window instanceof Response) return window;
    return answer(trapCounts(seed, window.from, window.to, scenario, now), scenario);
  }),
  aiRoute("device_health", "get", "/v1/devices/:id/health", ({ user, params, scenario, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    return seed ? answer(deviceHealth(seed, scenario, now), scenario) : notFound(scenario);
  }),
  /* Alertes : route du socle, seule la provenance dépend du service (null sous error_503). */
  aiRoute(
    "device_health",
    "get",
    "/v1/alerts",
    ({ user, query, scenario, now }) => {
      const limit = intParam(query, "limit", ALERTS_DEFAULT_LIMIT, 1, ALERTS_MAX_LIMIT);
      if (limit === null) return invalid(`« limit » entre 1 et ${ALERTS_MAX_LIMIT}.`);
      const status = query.get("status") ?? "all";
      const filter = ALERT_FILTERS.find((f) => f === status);
      if (!filter) return invalid("Statut d'alerte inconnu.", { allowed: ALERT_FILTERS });
      return answer(alertsView(visibleDeviceSeeds(user), filter, limit, scenario, now), scenario);
    },
    { unavailable: "resolve" },
  ),
  aiRoute(
    "device_health",
    "post",
    "/v1/alerts/:id/ack",
    ({ user, params, scenario, now }) => {
      const seed = alertSeedById(params.id ?? "");
      const device = seed ? visibleDevice(user, seed.deviceId) : null;
      if (!seed || !device) return notFound(scenario);
      if (!canAckAlerts(user.me, device.orgId)) return forbidden();
      if (alertView(seed, device, scenario, now).status === "open") acknowledgeAlert(seed.id, now);
      return answer(alertView(seed, device, scenario, now), scenario);
    },
    { unavailable: "resolve" },
  ),
];

/* ---------- Rapport et marchés (14, 15) ---------- */

const reportHandlers: HttpHandler[] = [
  aiRoute(
    "water_savings",
    "get",
    "/v1/reports/kpis",
    ({ user, query, scenario, now }) => {
      const report = reportRequest(user, query, now);
      if (report instanceof Response) return report;
      return answer(kpiReport(report.scope, report.from, report.to, scenario, now), scenario);
    },
    { unavailable: "resolve" },
  ),
  aiRoute("price_forecast", "get", "/v1/markets/prices", ({ query, scenario, now }) => {
    const crop = query.get("crop")?.trim().toLowerCase() ?? "";
    const market = query.get("market")?.trim() ?? "";
    if (!crop || !market) return invalid("« crop » et « market » obligatoires.", { crops: PRICE_CROPS });
    const forecast = priceForecast(crop, market, scenario, now);
    return forecast
      ? answer(forecast, scenario)
      : fail("NOT_FOUND", "Pas de prévision de prix pour cette culture.", 404, { details: { crops: PRICE_CROPS }, scenario });
  }),
];

/* ---------- Vision et assistant (8, 16, 17) ---------- */

/** Une photo se rattache à une parcelle ou à un kit du périmètre de l'utilisateur. */
function inScope(user: Principal, input: DiagnosisInput): boolean {
  if (input.field_id !== null && !visibleField(user, input.field_id)) return false;
  return input.device_id === null || visibleDevice(user, input.device_id) !== null;
}

async function diagnosisInput(ctx: AiContext): Promise<DiagnosisInput | Response> {
  const read = await readBoundedJson(ctx.request);
  if (read === "too_large") return tooLarge(ctx.scenario);
  const parsed = DiagnosisInputSchema.safeParse(read.body);
  if (!parsed.success) return invalid("Photo ou rattachement invalide.", { issues: parsed.error.issues.length });
  return inScope(ctx.user, parsed.data) ? parsed.data : notFound(ctx.scenario);
}

const assistantHandlers: HttpHandler[] = [
  aiRoute("disease_diagnosis", "post", "/v1/diagnoses/analyze", async (ctx) => {
    const input = await diagnosisInput(ctx);
    return input instanceof Response ? input : answer(diagnosis(input, null, ctx.scenario, ctx.now), ctx.scenario);
  }),
  aiRoute("disease_diagnosis", "post", "/v1/diagnoses", async (ctx) => {
    const input = await diagnosisInput(ctx);
    if (input instanceof Response) return input;
    const result = diagnosis(input, null, ctx.scenario, ctx.now);
    const rank = recordDiagnosis(result.label);
    return answer({ ...result, id: `diag-mock-${result.label}-${rank}` }, ctx.scenario, 201);
  }),
  aiRoute("assistant_chat", "post", "/v1/assistant/chat", async ({ request, user, scenario, now }) => {
    const read = await readBoundedJson(request);
    if (read === "too_large") return tooLarge(scenario);
    const parsed = ChatInputSchema.safeParse(read.body);
    if (!parsed.success) return fail("MESSAGE_INVALID", "Message vide ou trop long (2 000 caractères au plus).", 422, { scenario });
    const quota = recordChat(user.me.id, now);
    if (!quota.allowed) {
      return fail("RATE_LIMITED", "Trop de messages : réessayez dans quelques secondes.", 429, {
        headers: { "Retry-After": String(quota.retryAfterS) },
        scenario,
      });
    }
    return answer(chatReply(parsed.data, scenario, now), scenario);
  }),
  aiRoute("assistant_transcribe", "post", "/v1/assistant/transcribe", async ({ request, scenario, now }) => {
    const read = await readBoundedJson(request);
    if (read === "too_large") return tooLarge(scenario);
    const parsed = TranscribeInputSchema.safeParse(read.body);
    if (!parsed.success) return invalid("Enregistrement invalide (60 s au plus).");
    return answer(transcription(parsed.data, scenario, now), scenario);
  }),
];

export const aiHandlers: readonly HttpHandler[] = [
  ...fieldHandlers,
  feedbackHandler,
  ...farmHandlers,
  ...deviceHandlers,
  ...reportHandlers,
  ...assistantHandlers,
];

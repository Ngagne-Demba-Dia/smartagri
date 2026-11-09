/**
 * Les 18 services d'IA de doc 16 §9.3, gelés en baseline v1 : routes, modèles, disponibilité, modules web,
 * schéma de réponse et cibles de §9.4. Le front, les simulations (mocks/) et les tests de contrat lisent
 * cette table ; un service ajouté ou renommé passe d'abord par doc 16 (v1.x et ligne de changelog).
 */
import type { z } from "zod";

import { ChatResultSchema, DiagnosisSchema, TranscriptionSchema } from "./assistant";
import { AlertListSchema, DeviceHealthSchema, KitParametersSchema, TrapCountsSchema } from "./device";
import {
  FertilizationSchema,
  IrrigationNeedSchema,
  PestRiskSchema,
  RecommendationListSchema,
  SoilForecastSchema,
  VegetationSchema,
  WeatherSchema,
  YieldForecastSchema,
} from "./field";
import { IrrigationPlanSchema, KpiReportSchema, MapLayersSchema, PriceForecastSchema } from "./org";

export const SERVICE_IDS = [
  "weather",
  "soil_forecast",
  "irrigation_need",
  "irrigation_plan",
  "recommendations",
  "fertilization",
  "kit_parameters",
  "disease_diagnosis",
  "pest_risk",
  "trap_counts",
  "vegetation",
  "yield_forecast",
  "device_health",
  "water_savings",
  "price_forecast",
  "assistant_chat",
  "assistant_transcribe",
  "map_layers",
] as const;
export type ServiceId = (typeof SERVICE_IDS)[number];

/** existing : route déjà servie par l'API (forme gardée, champs ajoutés) ; proposed : route à créer. */
export type RouteStatus = "existing" | "proposed";
export type Availability = "MVP" | "V1.1" | "V2" | "V3";

export interface RouteDef {
  method: "GET" | "POST" | "PUT";
  path: string;
  status: RouteStatus;
}

export interface ServiceDef {
  number: number;
  id: ServiceId;
  routes: readonly RouteDef[];
  /** Identifiants du catalogue agriml (doc 14), dans l'ordre de la chaîne de repli. */
  models: readonly string[];
  availability: readonly Availability[];
  /** Numéros des modules web de doc 10 §3.2 qui affichent le service. */
  modules: readonly number[];
  /** Schéma de la donnée de la route principale (la première de `routes`). */
  schema: z.ZodType;
  /** Durée pendant laquelle le front garde la réponse sans la redemander (doc 16 §9.4). */
  staleMs: number;
  /** Latence simulée, sous la cible p95 de §9.4 quand elle existe. */
  mockLatencyMs: number;
}

const MIN = 60_000;
const HOUR = 60 * MIN;
const get = (path: string, status: RouteStatus): RouteDef => ({ method: "GET", path, status });
const post = (path: string, status: RouteStatus): RouteDef => ({ method: "POST", path, status });

export const SERVICES: readonly ServiceDef[] = [
  {
    number: 1, id: "weather", schema: WeatherSchema, staleMs: HOUR, mockLatencyMs: 350,
    routes: [get("/v1/fields/{id}/weather?days=", "existing")],
    models: ["wx_blend", "wx_rain_prob", "wx_local_bias", "irr_et0"], availability: ["MVP", "V2"], modules: [1, 5, 7],
  },
  {
    number: 2, id: "soil_forecast", schema: SoilForecastSchema, staleMs: 15 * MIN, mockLatencyMs: 300,
    routes: [get("/v1/fields/{id}/soil-forecast?horizons=24,48,72", "proposed")],
    models: ["soil_nowcast"], availability: ["V2"], modules: [1, 3],
  },
  {
    number: 3, id: "irrigation_need", schema: IrrigationNeedSchema, staleMs: 6 * HOUR, mockLatencyMs: 300,
    routes: [get("/v1/fields/{id}/irrigation-need", "proposed")],
    models: ["irr_need_24h", "irr_water_balance"], availability: ["MVP", "V2"], modules: [3, 7],
  },
  {
    number: 4, id: "irrigation_plan", schema: IrrigationPlanSchema, staleMs: 6 * HOUR, mockLatencyMs: 450,
    routes: [get("/v1/farms/{farm_id}/irrigation-plan?date=", "proposed")],
    models: ["irr_scheduler"], availability: ["V3"], modules: [7, 10],
  },
  {
    number: 5, id: "recommendations", schema: RecommendationListSchema, staleMs: 15 * MIN, mockLatencyMs: 400,
    routes: [get("/v1/fields/{id}/recommendations", "existing"), post("/v1/recommendations/{id}/feedback", "existing")],
    models: ["reco_engine", "risk_rules", "fert_reco"], availability: ["MVP"], modules: [1, 7],
  },
  {
    number: 6, id: "fertilization", schema: FertilizationSchema, staleMs: 6 * HOUR, mockLatencyMs: 400,
    routes: [get("/v1/fields/{id}/fertilization", "proposed")],
    models: ["fert_reco", "npk_calibration"], availability: ["V1.1", "V2"], modules: [6],
  },
  {
    number: 7, id: "kit_parameters", schema: KitParametersSchema, staleMs: HOUR, mockLatencyMs: 300,
    routes: [
      get("/v1/devices/{id}/parameters", "proposed"),
      get("/v1/devices/{id}/thresholds", "existing"),
      { method: "PUT", path: "/v1/devices/{id}/thresholds", status: "existing" },
    ],
    models: ["irr_water_balance", "sm_calibration", "fert_reco", "npk_calibration"], availability: ["V1.1"],
    modules: [3, 10],
  },
  {
    number: 8, id: "disease_diagnosis", schema: DiagnosisSchema, staleMs: 0, mockLatencyMs: 900,
    routes: [post("/v1/diagnoses/analyze", "proposed"), post("/v1/diagnoses", "existing")],
    models: ["vis_disease"], availability: ["V2"], modules: [8],
  },
  {
    number: 9, id: "pest_risk", schema: PestRiskSchema, staleMs: 6 * HOUR, mockLatencyMs: 350,
    routes: [get("/v1/fields/{id}/pest-risk", "proposed")],
    models: ["risk_rules", "pest_phenology", "pest_risk_ml"], availability: ["V1.1", "V2"], modules: [4, 7, 8],
  },
  {
    number: 10, id: "trap_counts", schema: TrapCountsSchema, staleMs: HOUR, mockLatencyMs: 350,
    routes: [get("/v1/devices/{id}/trap-counts?from=&to=", "proposed")],
    models: ["vis_pest_count"], availability: ["V3"], modules: [8],
  },
  {
    number: 11, id: "vegetation", schema: VegetationSchema, staleMs: 6 * HOUR, mockLatencyMs: 500,
    routes: [get("/v1/fields/{id}/vegetation?from=&to=", "proposed")],
    models: ["ndvi_gapfill", "phenology_stage", "vis_canopy"], availability: ["V2"], modules: [3, 4, 6],
  },
  {
    number: 12, id: "yield_forecast", schema: YieldForecastSchema, staleMs: 6 * HOUR, mockLatencyMs: 450,
    routes: [get("/v1/fields/{id}/yield-forecast?refresh=", "existing")],
    models: ["yield_forecast", "yield_crop_model"], availability: ["V3"], modules: [9, 11],
  },
  {
    number: 13, id: "device_health", schema: DeviceHealthSchema, staleMs: 5 * MIN, mockLatencyMs: 250,
    routes: [
      get("/v1/devices/{id}/health", "proposed"),
      get("/v1/alerts", "existing"),
      post("/v1/alerts/{id}/ack", "existing"),
    ],
    models: ["anomaly_rules", "anomaly_ml", "pump_health"], availability: ["MVP", "V2"], modules: [1, 10],
  },
  {
    number: 14, id: "water_savings", schema: KpiReportSchema, staleMs: HOUR, mockLatencyMs: 400,
    routes: [get("/v1/reports/kpis", "existing")],
    models: ["water_savings"], availability: ["V1.1"], modules: [1, 11, 13],
  },
  {
    number: 15, id: "price_forecast", schema: PriceForecastSchema, staleMs: 6 * HOUR, mockLatencyMs: 400,
    routes: [get("/v1/markets/prices?crop=&market=", "proposed")],
    models: ["price_forecast"], availability: ["V3"], modules: [11, 13],
  },
  {
    number: 16, id: "assistant_chat", schema: ChatResultSchema, staleMs: 0, mockLatencyMs: 1_800,
    routes: [post("/v1/assistant/chat", "existing")],
    models: ["asst_retrieval", "asst_llm", "asst_guard"], availability: ["MVP"], modules: [12],
  },
  {
    number: 17, id: "assistant_transcribe", schema: TranscriptionSchema, staleMs: 0, mockLatencyMs: 1_200,
    routes: [post("/v1/assistant/transcribe", "proposed")],
    models: ["asst_asr"], availability: ["V2"], modules: [12],
  },
  {
    number: 18, id: "map_layers", schema: MapLayersSchema, staleMs: 15 * MIN, mockLatencyMs: 450,
    routes: [get("/v1/farms/{farm_id}/map", "existing"), get("/v1/farms/{farm_id}/map?layers=crop_type,salinity", "proposed")],
    models: ["crop_type_map", "salinity_risk", "field_boundary"], availability: ["V3"], modules: [3, 4, 6],
  },
];

export function serviceById(id: ServiceId): ServiceDef {
  const found = SERVICES.find((s) => s.id === id);
  if (!found) throw new Error(`Service inconnu : ${id}`);
  return found;
}

/** Les alertes (13) n'ont pas de schéma propre dans la table : leur liste est validée à part. */
export const ALERTS_SCHEMA = AlertListSchema;

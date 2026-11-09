/**
 * Contrats des services d'IA rattachés à une parcelle (doc 16 §9.3–9.4, services 1, 2, 3, 5, 6, 9, 11, 12).
 * Routes existantes : la forme actuelle est gardée, les champs ajoutés (provenance, probabilité de pluie…)
 * sont des candidats v1.1 listés dans docs/17_frontend_v0_1.md et valent null tant que l'API ne les envoie pas.
 */
import { z } from "zod";

import { OptionalProvenance, ProvenanceSchema, isoDate, isoDateTime } from "./provenance";

const id = z.string().min(1);
const num = z.number().nullable();
const later = <T extends z.ZodType>(schema: T) => schema.nullable().default(null);

/* 1. weather — GET /v1/fields/{field_id}/weather?days= (existante) */
export const WeatherDaySchema = z.object({
  date: isoDate,
  t_max_c: num,
  t_min_c: num,
  precipitation_mm: num,
  et0_mm: num,
  et0_hargreaves_mm: num,
  rain_probability: later(z.number().min(0).max(1)),
  rain_threshold_mm: later(z.number().min(0)),
  local_bias_c: later(z.number()),
});
export const WeatherSchema = z.object({
  field_id: id,
  location_source: z.string(),
  provider: z.string(),
  latitude: z.number(),
  longitude: z.number(),
  fetched_at: isoDateTime,
  source: z.enum(["provider", "cache", "stale_cache"]),
  days: z.array(WeatherDaySchema),
  provenance: OptionalProvenance,
});

/* 2. soil_forecast — GET /v1/fields/{id}/soil-forecast?horizons=24,48,72 (proposée) */
export const SoilForecastSchema = z.object({
  field_id: id,
  device_id: id.nullable(),
  issued_at: isoDateTime,
  horizons: z.array(z.object({ hours: z.number().int().positive(), p10: z.number(), p50: z.number(), p90: z.number() })),
  thresholds: z.object({ start_pct: z.number(), stop_pct: z.number() }).nullable(),
  provenance: ProvenanceSchema,
});

/* 3. irrigation_need — GET /v1/fields/{id}/irrigation-need (proposée) */
export const IrrigationNeedSchema = z.object({
  field_id: id,
  window_hours: z.literal(24),
  need_mm: z.number().min(0),
  volume_m3: num,
  defer: z.boolean(),
  defer_reason: z.string().nullable(),
  rain_expected_mm: num,
  provenance: ProvenanceSchema,
});

/* 5. recommendations — GET /v1/fields/{id}/recommendations (existante) + POST …/feedback */
const IrrigationPayloadSchema = z.object({
  advice: z.object({
    action: z.enum(["verifier_capteur", "irriguer", "surveiller", "ne_pas_irriguer"]),
    reason: z.string(),
    etc_mm: num,
    net_mm: num,
    gross_mm: num,
    volume_m3: num,
    caveat: z.string(),
  }),
  crop: z.string().nullable(),
  et0_mm: num,
  et0_method: z.string().nullable(),
  thresholds: z.object({ start_pct: z.number(), stop_pct: z.number(), source: z.string() }),
  measured_at: isoDateTime.nullable(),
  device_serial: z.string().nullable(),
});
const FertilizationPayloadSchema = z.object({
  nutrients: z.array(
    z.object({ nutrient: z.string(), value: num, level: z.enum(["bas", "moyen", "eleve"]).nullable(), message: z.string() }),
  ),
  sensor_ok: z.boolean(),
  caveat: z.string(),
});
const recoCommon = {
  id,
  engine_version: z.string(),
  created_at: isoDateTime.nullable(),
  priority: later(z.enum(["high", "medium", "low"])),
  valid_until: later(isoDateTime),
  justification: later(z.string()),
  provenance: OptionalProvenance,
};
export const RecommendationSchema = z.discriminatedUnion("kind", [
  z.object({ ...recoCommon, kind: z.literal("irrigation"), payload: IrrigationPayloadSchema }),
  z.object({ ...recoCommon, kind: z.literal("fertilization"), payload: FertilizationPayloadSchema }),
]);
export const RecommendationListSchema = z.array(RecommendationSchema);
export const FEEDBACK_VALUES = ["followed", "partially_followed", "ignored", "not_applicable"] as const;
export const FeedbackInputSchema = z.object({ feedback: z.enum(FEEDBACK_VALUES) });

/* 6. fertilization — GET /v1/fields/{id}/fertilization (proposée) ; « indicatif » tant que non étalonné */
export const FertilizationSchema = z.object({
  field_id: id,
  crop: z.string().nullable(),
  stage: z.string().nullable(),
  n_kg_ha: num,
  p_kg_ha: num,
  k_kg_ha: num,
  npk_class: z.enum(["bas", "moyen", "eleve"]).nullable(),
  indicative: z.boolean(),
  caveat: z.string(),
  provenance: ProvenanceSchema,
});

/* 9. pest_risk — GET /v1/fields/{id}/pest-risk (proposée) */
export const PestRiskSchema = z.object({
  field_id: id,
  pests: z.array(
    z.object({
      pest_code: z.string(),
      level: z.enum(["low", "medium", "high"]),
      p_outbreak_7d: z.number().min(0).max(1).nullable(),
      p_outbreak_14d: z.number().min(0).max(1).nullable(),
      factors: z.array(z.string()),
    }),
  ),
  provenance: ProvenanceSchema,
});

/* 11. vegetation — GET /v1/fields/{id}/vegetation?from=&to= (proposée) */
export const VegetationSchema = z.object({
  field_id: id,
  from: isoDate,
  to: isoDate,
  series: z.array(z.object({ date: isoDate, ndvi: num, evi: num, gapfilled: z.boolean() })),
  stage: z.object({ bbch: z.number().int().min(0).max(99), label: z.string() }).nullable(),
  canopy_cover_pct: num,
  provenance: ProvenanceSchema,
});

/* 12. yield_forecast — GET /v1/fields/{id}/yield-forecast?refresh= (existante) ; 404 NO_ACTIVE_CYCLE */
export const YieldForecastSchema = z.object({
  field_id: id,
  crop_cycle: z.object({
    id,
    crop: z.string(),
    status: z.enum(["planned", "active", "harvested", "abandoned"]),
    planted_on: isoDate.nullable(),
  }),
  forecast: z
    .object({
      id,
      model_name: z.string(),
      model_version: z.string(),
      predicted_t_ha: num,
      p10: num,
      p90: num,
      created_at: isoDateTime,
    })
    .nullable(),
  actual_t_ha: num,
  caveat: z.string(),
  provenance: OptionalProvenance,
});

export type WeatherForecastView = z.infer<typeof WeatherSchema>;
export type SoilForecast = z.infer<typeof SoilForecastSchema>;
export type IrrigationNeed = z.infer<typeof IrrigationNeedSchema>;
export type RecommendationView = z.infer<typeof RecommendationSchema>;
export type Fertilization = z.infer<typeof FertilizationSchema>;
export type PestRisk = z.infer<typeof PestRiskSchema>;
export type Vegetation = z.infer<typeof VegetationSchema>;
export type YieldForecast = z.infer<typeof YieldForecastSchema>;

/**
 * Contrats à l'échelle de l'exploitation ou de l'organisation (doc 16 §9.3–9.4, services 4, 14, 15 et 18).
 */
import { z } from "zod";

import { OptionalProvenance, ProvenanceSchema, isoDate, isoDateTime } from "./provenance";

const id = z.string().min(1);
const num = z.number().nullable();

/* 4. irrigation_plan — GET /v1/farms/{farm_id}/irrigation-plan?date= (proposée) */
export const IrrigationPlanSchema = z.object({
  farm_id: id,
  date: isoDate,
  slots: z.array(
    z.object({
      field_id: id,
      pump_id: id,
      start: isoDateTime,
      end: isoDateTime,
      volume_m3: z.number().min(0),
    }),
  ),
  provenance: ProvenanceSchema,
});

/* 14. water_savings — dans GET /v1/reports/kpis (existante) : bloc ajouté, méthode des parcelles témoins */
export const WaterSavingsSchema = z.object({
  saved_m3: num,
  saved_pct: num,
  method: z.string(),
  control_fields: z.number().int().min(0),
  provenance: ProvenanceSchema,
});
export const KpiReportSchema = z.object({
  scope: z.enum(["org", "farm", "field"]),
  scope_id: id,
  from: z.string(),
  to: z.string(),
  kpis: z.object({
    devices: z.number(),
    fields: z.number(),
    water_m3: num,
    devices_without_flow: z.number(),
    pump_hours: z.number(),
    irrigation_events: z.number(),
    measurements: z.number(),
    kit_uptime_pct: num,
    alerts_by_rule: z.record(z.string(), z.number()),
    diagnoses_by_label: z.record(z.string(), z.number()),
    recommendations_feedback: z.record(z.string(), z.number()),
    recommendations_followed_pct: num,
    water_savings: WaterSavingsSchema.nullable().default(null),
  }),
});

/* 15. price_forecast — GET /v1/markets/prices?crop=&market= (proposée) ; FCFA/kg */
export const PriceForecastSchema = z.object({
  crop: z.string(),
  market: z.string(),
  currency: z.literal("XOF"),
  unit: z.literal("kg"),
  observed: z.object({ date: isoDate, price: z.number().min(0) }).nullable(),
  horizons: z.array(z.object({ weeks: z.number().int().min(1).max(4), p10: z.number(), p50: z.number(), p90: z.number() })),
  provenance: ProvenanceSchema,
});

/* 18. map_layers — GET /v1/farms/{farm_id}/map (existante) + ?layers=crop_type,salinity (proposée) */
export const MAP_LAYERS = ["crop_type", "salinity", "field_boundary"] as const;
export type MapLayer = (typeof MAP_LAYERS)[number];

const FieldPropsSchema = z.object({
  kind: z.literal("field"),
  field_id: id,
  name: z.string(),
  area_ha: num,
  crop: z.string().nullable(),
  soil_moisture_pct: num,
  open_alerts: z.number().int().min(0),
  crop_type: z.object({ label: z.string(), probability: z.number().min(0).max(1).nullable() }).nullable().default(null),
  salinity_class: z.enum(["none", "low", "moderate", "high"]).nullable().default(null),
  ndvi: num.default(null),
});
const DevicePropsSchema = z.object({
  kind: z.literal("device"),
  device_id: id,
  serial: z.string(),
  field_id: id.nullable(),
  status: z.enum(["active", "inactive", "retired"]),
  soil_moisture_pct: num,
  measured_at: isoDateTime.nullable(),
  last_seen_at: isoDateTime.nullable(),
  open_alerts: z.number().int().min(0),
  position_estimated: z.boolean(),
});
const BoundaryPropsSchema = z.object({ kind: z.literal("boundary"), field_id: id, area_ha: num });
const geometry = z.object({ type: z.string(), coordinates: z.unknown() }).nullable();

export const MapLayersSchema = z.object({
  type: z.literal("FeatureCollection"),
  features: z.array(
    z.object({
      type: z.literal("Feature"),
      id,
      geometry,
      properties: z.discriminatedUnion("kind", [FieldPropsSchema, DevicePropsSchema, BoundaryPropsSchema]),
    }),
  ),
  /** Provenance par couche demandée (crop_type_map, salinity_risk, field_boundary). */
  layers: z.record(z.string(), ProvenanceSchema).default({}),
  provenance: OptionalProvenance,
});

export type IrrigationPlan = z.infer<typeof IrrigationPlanSchema>;
export type WaterSavings = z.infer<typeof WaterSavingsSchema>;
export type KpiReportView = z.infer<typeof KpiReportSchema>;
export type PriceForecast = z.infer<typeof PriceForecastSchema>;
export type MapLayersView = z.infer<typeof MapLayersSchema>;
export type MapFeatureView = MapLayersView["features"][number];

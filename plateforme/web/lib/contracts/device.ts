/**
 * Contrats rattachés à un kit (doc 16 §9.3–9.4, services 7, 10 et 13) et jeu de paramètres de doc 16 §6.1.
 */
import { z } from "zod";

import { OptionalProvenance, ProvenanceSchema, isoDate, isoDateTime } from "./provenance";

const id = z.string().min(1);

/* 7. kit_parameters — GET /v1/devices/{device_id}/parameters (proposée) ; seuils : GET/PUT …/thresholds (existantes) */
export const ADC_MAX = 4095;
export const NPK_MAX_MGKG = 2000;
export const KC_MIN = 0.1;
export const KC_MAX = 1.5;
/** Durées de validité de doc 16 §6.1, en jours, au-delà desquelles le bloc est « périmé ». */
export const PARAM_VALIDITY_DAYS = { seuils: 7, npk: 30, etalonnage: 180, agro: 30 } as const;

export const KitParametersSchema = z
  .object({
    device_id: id,
    version: z.number().int().min(1),
    emis_a: isoDateTime,
    seuils: z.object({ start: z.number().int().min(0), stop: z.number().int().max(100) }),
    npk: z.object({
      n: z.number().min(0).max(NPK_MAX_MGKG),
      p: z.number().min(0).max(NPK_MAX_MGKG),
      k: z.number().min(0).max(NPK_MAX_MGKG),
    }),
    etalonnage: z.object({ adc_sec: z.number().int().max(ADC_MAX), adc_eau: z.number().int().min(0) }),
    agro: z.object({
      culture: z.string().nullable(),
      stade: z.string().nullable(),
      date_semis: isoDate.nullable(),
      kc: z.number().min(KC_MIN).max(KC_MAX).nullable(),
    }),
    /** « seuil conseillé » tant que l'utilisateur ne l'a pas appliqué par PUT …/thresholds. */
    applied: z.boolean(),
    provenance: z.object({
      seuils: ProvenanceSchema,
      npk: ProvenanceSchema,
      etalonnage: ProvenanceSchema,
      agro: ProvenanceSchema,
    }),
  })
  .superRefine((p, ctx) => {
    if (p.seuils.start + 5 > p.seuils.stop) ctx.addIssue({ code: "custom", message: "seuils : start + 5 ≤ stop", path: ["seuils"] });
    if (p.etalonnage.adc_eau >= p.etalonnage.adc_sec) {
      ctx.addIssue({ code: "custom", message: "etalonnage : adc_eau < adc_sec", path: ["etalonnage"] });
    }
  });

/* 10. trap_counts — GET /v1/devices/{id}/trap-counts?from=&to= (proposée) */
export const TrapCountsSchema = z.object({
  device_id: id,
  from: isoDateTime,
  to: isoDateTime,
  pest_code: z.string(),
  series: z.array(z.object({ captured_at: isoDateTime, count: z.number().int().min(0), image_id: z.string().nullable() })),
  provenance: ProvenanceSchema,
});

/* 13. device_health — GET /v1/alerts + POST /v1/alerts/{id}/ack (existantes), GET /v1/devices/{id}/health (proposée) */
export const SENSOR_STATES = ["ok", "degraded", "fault", "absent"] as const;
export const DeviceHealthSchema = z.object({
  device_id: id,
  checked_at: isoDateTime,
  sensors: z.array(
    z.object({
      sensor: z.enum(["soil", "bme", "npk", "flow", "pump", "battery"]),
      state: z.enum(SENSOR_STATES),
      since: isoDateTime.nullable(),
    }),
  ),
  pump_failure_48h: z.number().min(0).max(1).nullable(),
  provenance: ProvenanceSchema,
});

export const AlertSchema = z.object({
  id,
  organization_id: id,
  device_id: id.nullable(),
  field_id: id.nullable(),
  rule: z.string(),
  severity: z.enum(["info", "warning", "critical"]),
  status: z.enum(["open", "acknowledged", "resolved"]),
  message: z.string(),
  details: z.record(z.string(), z.unknown()).nullable(),
  created_at: isoDateTime,
  acknowledged_at: isoDateTime.nullable(),
  resolved_at: isoDateTime.nullable(),
  provenance: OptionalProvenance,
});
export const AlertListSchema = z.array(AlertSchema);

export type KitParameters = z.infer<typeof KitParametersSchema>;
export type ParameterBlock = keyof KitParameters["provenance"];
export type TrapCounts = z.infer<typeof TrapCountsSchema>;
export type DeviceHealth = z.infer<typeof DeviceHealthSchema>;
export type SensorState = (typeof SENSOR_STATES)[number];
export type AlertView = z.infer<typeof AlertSchema>;

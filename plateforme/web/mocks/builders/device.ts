/**
 * Réponses simulées rattachées à un kit : fiche, mesures, paramètres poussés (doc 16 §6.1),
 * pièges, santé et alertes. Fonctions pures de (graine, scénario, now) et de l'état du store.
 */
import type { AlertView, DeviceHealth, KitParameters, SensorState, TrapCounts } from "@/lib/contracts/device";
import type { Device, DeviceDetail } from "@/lib/types";

import { DAY_MS, HOUR_MS, iso, isoDay, round } from "../base";
import {
  ALERT_SEEDS,
  FIRMWARE_VERSION,
  fieldSeedById,
  hoursBefore,
  lastSeen,
  type AlertSeed,
  type DeviceSeed,
} from "../fixtures/places";
import { bbchStage, between, latestMeasurement } from "../fixtures/series";
import { KIT_BLOCK_MODELS, NO_CONFIDENCE, interval, provenance } from "../provenance";
import type { MockScenario } from "../scenario";
import { alertOverride, effectiveThresholds, thresholdState } from "../store";

import { cropKc, pestsOf, plantedDate } from "./common";

export function deviceView(seed: DeviceSeed, now: Date): Device {
  return {
    id: seed.id,
    serial: seed.serial,
    name: `Kit ${seed.serial}`,
    organization_id: seed.orgId,
    field_id: seed.fieldId,
    firmware_version: FIRMWARE_VERSION,
    status: seed.status,
    last_seen_at: iso(lastSeen(seed, now)),
    thresholds: thresholdState(seed.id, now),
  };
}

export function deviceDetail(seed: DeviceSeed, now: Date): DeviceDetail {
  const at = lastSeen(seed, now);
  return {
    ...deviceView(seed, now),
    latest_measurement: latestMeasurement(seed.id, at, effectiveThresholds(seed.id, now), seed.npk, FIRMWARE_VERSION),
  };
}

/* ---------- 7. kit_parameters ---------- */

const PARAM_VERSION = 3;
const PARAM_ISSUED_AGO_MS = 2 * HOUR_MS;
/** Seuils de démarrage et d'arrêt conseillés par type de sol (irr_water_balance, doc 14 § 4.2.1). */
const ADVISED_BY_SOIL: readonly { match: string; start: number; stop: number }[] = [
  { match: "dior", start: 28, stop: 55 },
  { match: "deck", start: 32, stop: 62 },
  { match: "hollald", start: 38, stop: 70 },
];
const DEFAULT_ADVICE = { start: 30, stop: 60 };
const NPK_ALERT_LEVELS = { n: 20, p: 10, k: 80 } as const;

export function advisedThresholds(soil: string): { start: number; stop: number } {
  const lower = soil.toLowerCase();
  const hit = ADVISED_BY_SOIL.find((s) => lower.includes(s.match));
  return hit ? { start: hit.start, stop: hit.stop } : { ...DEFAULT_ADVICE };
}

/** null : pas de jeu de paramètres publié (scénario « empty », 404). */
export function kitParameters(seed: DeviceSeed, scenario: MockScenario, now: Date): KitParameters | null {
  if (scenario === "empty") return null;
  const field = fieldSeedById(seed.fieldId);
  const seuils = advisedThresholds(field?.soil ?? "");
  const effective = effectiveThresholds(seed.id, now);
  const abstain = scenario === "abstention";
  const planted = field ? plantedDate(field, now) : null;
  const issued = new Date(now.getTime() - PARAM_ISSUED_AGO_MS);
  const block = (name: keyof typeof KIT_BLOCK_MODELS) =>
    provenance("kit_parameters", scenario, now, { model: KIT_BLOCK_MODELS[name], dataAsOf: issued });
  return {
    device_id: seed.id,
    version: PARAM_VERSION,
    emis_a: iso(issued),
    seuils,
    npk: { ...NPK_ALERT_LEVELS },
    etalonnage: {
      adc_sec: Math.round(between(`${seed.id}:adc_sec`, 3150, 3250)),
      adc_eau: Math.round(between(`${seed.id}:adc_eau`, 1300, 1400)),
    },
    agro: {
      culture: field?.crop ?? null,
      stade: abstain || !field?.crop ? null : bbchStage(field.plantedDaysAgo, field.cycleDays).label,
      date_semis: planted ? isoDay(planted) : null,
      kc: abstain || !field?.crop ? null : cropKc(field),
    },
    applied: effective.start_pct === seuils.start && effective.stop_pct === seuils.stop,
    provenance: { seuils: block("seuils"), npk: block("npk"), etalonnage: block("etalonnage"), agro: block("agro") },
  };
}

/* ---------- 10. trap_counts ---------- */

export const TRAP_DEFAULT_DAYS = 14;
export const TRAP_MAX_DAYS = 92;
const CAPTURE_HOUR_UTC = 7;

export function trapCounts(seed: DeviceSeed, from: Date, to: Date, scenario: MockScenario, now: Date): TrapCounts {
  const field = fieldSeedById(seed.fieldId);
  const pest = (field ? pestsOf(field)[0] : undefined) ?? "generic";
  const end = Math.min(to.getTime(), lastSeen(seed, now).getTime());
  const series: TrapCounts["series"] = [];
  if (scenario !== "empty" && scenario !== "abstention") {
    const first = new Date(`${isoDay(from)}T0${CAPTURE_HOUR_UTC}:00:00Z`).getTime();
    for (let t = first; t <= end; t += DAY_MS) {
      if (t < from.getTime()) continue;
      const day = isoDay(new Date(t));
      series.push({
        captured_at: iso(new Date(t)),
        count: Math.round(between(`${seed.id}:${pest}:${day}`, 0, 14)),
        image_id: `img-${seed.id}-${day}`,
      });
    }
  }
  const last = series[series.length - 1];
  const counts = series.map((s) => s.count);
  return {
    device_id: seed.id,
    from: iso(from),
    to: iso(to),
    pest_code: pest,
    series,
    provenance: provenance("trap_counts", scenario, now, {
      confidence: counts.length ? interval(Math.min(...counts), Math.max(...counts), false) : NO_CONFIDENCE,
      dataAsOf: last ? new Date(last.captured_at) : null,
    }),
  };
}

/* ---------- 13. device_health ---------- */

type Sensor = DeviceHealth["sensors"][number]["sensor"];
const SENSORS: readonly Sensor[] = ["soil", "bme", "npk", "flow", "pump", "battery"];
const FLOW_ABSENT = new Set(["dev-0002", "dev-0003", "dev-0004"]);
const PUMP_FAILURE_RISKY = 0.62;

function sensorState(seed: DeviceSeed, sensor: Sensor, now: Date): { state: SensorState; since: string | null } {
  const alertTime = (alertId: string) => {
    const alert = ALERT_SEEDS.find((a) => a.id === alertId);
    return alert ? iso(hoursBefore(now, alert.hoursAgo)) : null;
  };
  if (seed.status !== "active" && (sensor === "soil" || sensor === "bme" || sensor === "npk")) {
    return { state: "degraded", since: iso(lastSeen(seed, now)) };
  }
  if (seed.id === "dev-0001" && sensor === "bme") return { state: "degraded", since: alertTime("alt-0004") };
  if (seed.id === "dev-0101" && sensor === "flow") return { state: "fault", since: alertTime("alt-0005") };
  if (seed.id === "dev-0101" && sensor === "pump") return { state: "degraded", since: alertTime("alt-0005") };
  if (sensor === "flow" && FLOW_ABSENT.has(seed.id)) return { state: "absent", since: null };
  return { state: "ok", since: null };
}

/** Le débitmètre manque ou est en défaut : volume d'eau non mesuré (rapport KPI). */
export const flowMissing = (seed: DeviceSeed, now: Date): boolean => sensorState(seed, "flow", now).state !== "ok";

export function deviceHealth(seed: DeviceSeed, scenario: MockScenario, now: Date): DeviceHealth {
  const checked = lastSeen(seed, now);
  const risk = seed.id === "dev-0101" ? PUMP_FAILURE_RISKY : round(between(`${seed.id}:pump48`, 0.02, 0.12), 2);
  const hideRisk = scenario === "abstention" || scenario === "fallback";
  return {
    device_id: seed.id,
    checked_at: iso(checked),
    sensors: scenario === "empty" ? [] : SENSORS.map((sensor) => ({ sensor, ...sensorState(seed, sensor, now) })),
    pump_failure_48h: hideRisk || scenario === "empty" ? null : risk,
    provenance: provenance("device_health", scenario, now, { dataAsOf: checked }),
  };
}

/* ---------- Alertes (route du socle enrichie de la provenance de device_health) ---------- */

const ALERT_ACK_DELAY_MS = HOUR_MS;
const ALERT_RESOLVE_DELAY_MS = 6 * HOUR_MS;
const ALERT_MODEL = { name: "anomaly_rules", version: "3", source: "rules" } as const;

export function alertView(seed: AlertSeed, device: DeviceSeed, scenario: MockScenario, now: Date): AlertView {
  const created = hoursBefore(now, seed.hoursAgo);
  const override = alertOverride(seed.id);
  const status = override?.status ?? seed.status;
  const ackedAt =
    status === "open" ? null : (override?.at ?? iso(new Date(created.getTime() + ALERT_ACK_DELAY_MS)));
  return {
    id: seed.id,
    organization_id: device.orgId,
    device_id: device.id,
    field_id: device.fieldId,
    rule: seed.rule,
    severity: seed.severity,
    status,
    message: seed.message,
    details: seed.details,
    created_at: iso(created),
    acknowledged_at: ackedAt,
    resolved_at: status === "resolved" ? iso(new Date(created.getTime() + ALERT_RESOLVE_DELAY_MS)) : null,
    provenance:
      scenario === "error_503"
        ? null
        : provenance("device_health", scenario, now, { model: ALERT_MODEL, dataAsOf: created }),
  };
}

export type AlertFilter = "open" | "acknowledged" | "resolved" | "all";

export function alertsView(
  devices: readonly DeviceSeed[],
  filter: AlertFilter,
  limit: number,
  scenario: MockScenario,
  now: Date,
): AlertView[] {
  if (scenario === "empty") return [];
  const byId = new Map(devices.map((d) => [d.id, d]));
  return ALERT_SEEDS.flatMap((seed) => {
    const device = byId.get(seed.deviceId);
    return device ? [alertView(seed, device, scenario, now)] : [];
  })
    .filter((a) => filter === "all" || a.status === filter)
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .slice(0, limit);
}

/** Alertes ouvertes d'un kit (badges de la carte), indépendantes du scénario. */
export function openAlertCount(deviceId: string): number {
  return ALERT_SEEDS.filter((a) => a.deviceId === deviceId && (alertOverride(a.id)?.status ?? a.status) === "open").length;
}

export const alertSeedById = (alertId: string): AlertSeed | null => ALERT_SEEDS.find((a) => a.id === alertId) ?? null;

/**
 * Vue d'ensemble du tableau de bord : une ligne par parcelle, verdict d'abord (doc 10 §2).
 * Sources : GET /v1/farms/{id}/map (humidité, alertes ouvertes par parcelle et par kit)
 * et GET /v1/devices (seuils voulus et état de synchronisation).
 */
import { deviceFreshness, moistureVerdict, type Freshness, type MoistureVerdict } from "./status";
import type { DeviceFeatureProps, Device, FarmMap, FieldFeatureProps, SyncStatus, ThresholdPair } from "./types";

export interface FieldOverview {
  fieldId: string;
  farmId: string;
  name: string;
  crop: string | null;
  areaHa: number | null;
  moisture: number | null;
  verdict: MoistureVerdict;
  /** null : aucun kit rattaché à la parcelle. */
  freshness: Freshness | null;
  deviceId: string | null;
  deviceSerial: string | null;
  lastSeenAt: string | null;
  thresholds: ThresholdPair | null;
  syncStatus: SyncStatus | null;
  openAlerts: number;
}

/** Ordre d'urgence : sol sec, puis kit silencieux, puis état inconnu, puis sol très humide, puis normal. */
function urgency(row: FieldOverview): number {
  if (row.verdict === "dry") return 0;
  if (row.freshness === "silent") return 1;
  if (row.verdict === "unknown") return 2;
  if (row.verdict === "wet") return 3;
  return 4;
}

function fieldProps(map: FarmMap): FieldFeatureProps[] {
  return map.features.flatMap((f) => (f.properties.kind === "field" ? [f.properties] : []));
}

function deviceProps(map: FarmMap): DeviceFeatureProps[] {
  return map.features.flatMap((f) => (f.properties.kind === "device" ? [f.properties] : []));
}

export function buildOverview(
  maps: ReadonlyArray<{ farmId: string; map: FarmMap }>,
  devices: readonly Device[],
  now: Date = new Date(),
): FieldOverview[] {
  const deviceById = new Map(devices.map((d) => [d.id, d]));
  const rows = maps.flatMap(({ farmId, map }) => {
    const kitByField = new Map(
      deviceProps(map).flatMap((kit) => (kit.field_id !== null ? [[kit.field_id, kit] as const] : [])),
    );
    return fieldProps(map).map((props): FieldOverview => {
      const kit = kitByField.get(props.field_id) ?? null;
      const device = kit ? (deviceById.get(kit.device_id) ?? null) : null;
      const thresholds = device?.thresholds?.desired ?? null;
      const moisture = props.soil_moisture_pct ?? kit?.soil_moisture_pct ?? null;
      return {
        fieldId: props.field_id,
        farmId,
        name: props.name,
        crop: props.crop,
        areaHa: props.area_ha,
        moisture,
        verdict: moistureVerdict(moisture, thresholds),
        freshness: kit ? deviceFreshness({ last_seen_at: kit.last_seen_at }, now) : null,
        deviceId: kit?.device_id ?? null,
        deviceSerial: kit?.serial ?? null,
        lastSeenAt: kit?.last_seen_at ?? null,
        thresholds,
        syncStatus: device?.thresholds?.sync_status ?? null,
        openAlerts: props.open_alerts,
      };
    });
  });
  return [...rows].sort((a, b) => urgency(a) - urgency(b) || a.name.localeCompare(b.name, "fr"));
}

export interface OverviewCounts {
  fields: number;
  dry: number;
  silentKits: number;
  openAlerts: number;
}

export function countOverview(rows: readonly FieldOverview[]): OverviewCounts {
  return {
    fields: rows.length,
    dry: rows.filter((r) => r.verdict === "dry").length,
    silentKits: rows.filter((r) => r.freshness === "silent").length,
    openAlerts: rows.reduce((sum, r) => sum + r.openAlerts, 0),
  };
}

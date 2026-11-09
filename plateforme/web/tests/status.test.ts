/**
 * Verdicts et états (lib/status.ts), vue d'ensemble du tableau de bord (lib/overview.ts)
 * et règle des seuils d'irrigation (lib/thresholds.ts, identique au firmware v1.1 et au backend).
 */
import { describe, expect, it } from "vitest";

import { buildOverview, countOverview } from "@/lib/overview";
import { FRESH_MS, STALE_MS, deviceFreshness, moistureRamp, moistureVerdict } from "@/lib/status";
import { THRESHOLD_MIN_GAP, parseThresholdInt, thresholdsValid, validateThresholds } from "@/lib/thresholds";
import type {
  Device,
  DeviceFeatureProps,
  FarmMap,
  FieldFeatureProps,
  MapFeature,
  MapFeatureProps,
} from "@/lib/types";

const NOW = new Date("2026-11-09T12:00:00Z");
const ago = (ms: number) => new Date(NOW.getTime() - ms).toISOString();
const PAIR = { start_pct: 30, stop_pct: 60 };

describe("moistureVerdict", () => {
  it.each([
    [29, "dry"],
    [30, "ok"],
    [60, "ok"],
    [61, "wet"],
  ])("%i %% avec seuils 30–60 → %s", (moisture, verdict) => {
    expect(moistureVerdict(moisture, PAIR)).toBe(verdict);
  });

  it("inconnu sans mesure ou sans seuils", () => {
    expect(moistureVerdict(null, PAIR)).toBe("unknown");
    expect(moistureVerdict(undefined, PAIR)).toBe("unknown");
    expect(moistureVerdict(45, null)).toBe("unknown");
  });
});

describe("deviceFreshness", () => {
  it.each([
    [0, "fresh"],
    [FRESH_MS, "fresh"],
    [FRESH_MS + 1, "late"],
    [STALE_MS, "late"],
    [STALE_MS + 1, "silent"],
  ])("vu il y a %i ms → %s", (ms, freshness) => {
    expect(deviceFreshness({ last_seen_at: ago(ms) }, NOW)).toBe(freshness);
  });

  it("jamais vu ou date illisible → silencieux", () => {
    expect(deviceFreshness({ last_seen_at: null }, NOW)).toBe("silent");
    expect(deviceFreshness({ last_seen_at: "illisible" }, NOW)).toBe("silent");
  });
});

describe("moistureRamp", () => {
  it.each([
    [null, 0],
    [Number.NaN, 0],
    [-5, 1],
    [0, 1],
    [19.9, 1],
    [20, 2],
    [59, 3],
    [79.9, 4],
    [80, 5],
    [100, 5],
    [140, 5],
  ])("%s %% → pas %i", (moisture, step) => {
    expect(moistureRamp(moisture)).toBe(step);
  });
});

/* ---------- Vue d'ensemble ---------- */

const field = (
  id: string,
  name: string,
  moisture: number | null,
  openAlerts = 0,
): MapFeature<MapFeatureProps> => ({
  type: "Feature",
  id,
  geometry: null,
  properties: {
    kind: "field",
    field_id: id,
    name,
    area_ha: 0.5,
    crop: "oignon",
    soil_moisture_pct: moisture,
    open_alerts: openAlerts,
  } satisfies FieldFeatureProps,
});

const kit = (
  deviceId: string,
  fieldId: string | null,
  lastSeen: string | null,
  moisture: number | null = null,
): MapFeature<MapFeatureProps> => ({
  type: "Feature",
  id: deviceId,
  geometry: null,
  properties: {
    kind: "device",
    device_id: deviceId,
    serial: `SA92-${deviceId}`,
    field_id: fieldId,
    status: "active",
    soil_moisture_pct: moisture,
    measured_at: lastSeen,
    last_seen_at: lastSeen,
    open_alerts: 0,
    position_estimated: false,
  } satisfies DeviceFeatureProps,
});

const device = (id: string, fieldId: string, withThresholds = true): Device => ({
  id,
  serial: `SA92-${id}`,
  name: null,
  organization_id: "org-a",
  field_id: fieldId,
  firmware_version: "1.1",
  status: "active",
  last_seen_at: null,
  thresholds: withThresholds
    ? { desired: PAIR, reported: null, sync_status: "pending", command_id: null, updated_at: null }
    : null,
});

describe("buildOverview et countOverview", () => {
  const map: FarmMap = {
    type: "FeatureCollection",
    features: [
      field("f-ok", "Bêta", 45, 1),
      field("f-dry", "Zêta", 20, 2),
      field("f-silent", "Alpha", 45),
      field("f-unknown", "Delta", null),
      field("f-wet", "Gamma", 80),
      field("f-ok2", "Alpha bis", 40),
      kit("d-ok", "f-ok", ago(60_000)),
      kit("d-dry", "f-dry", ago(60_000)),
      kit("d-silent", "f-silent", ago(STALE_MS + 1)),
      kit("d-unknown", "f-unknown", ago(60_000), 33),
      kit("d-wet", "f-wet", ago(FRESH_MS + 1)),
      kit("d-orphan", null, ago(60_000)),
    ],
  };
  const devices = [
    device("d-ok", "f-ok"),
    device("d-dry", "f-dry"),
    device("d-silent", "f-silent"),
    device("d-unknown", "f-unknown", false),
    device("d-wet", "f-wet"),
  ];
  const rows = buildOverview([{ farmId: "farm-a", map }], devices, NOW);

  it("trie par urgence : sec, silencieux, inconnu, très humide, normal (puis par nom)", () => {
    // f-ok2 n'a pas de kit, donc pas de seuils : verdict inconnu, classé avec f-unknown par ordre alphabétique.
    expect(rows.map((r) => r.fieldId)).toEqual(["f-dry", "f-silent", "f-ok2", "f-unknown", "f-wet", "f-ok"]);
  });

  it("reprend l'humidité du kit quand la parcelle n'en a pas, et les seuils voulus du kit", () => {
    const unknown = rows.find((r) => r.fieldId === "f-unknown");
    expect(unknown?.moisture).toBe(33);
    expect(unknown?.thresholds).toBeNull();
    expect(unknown?.verdict).toBe("unknown");
    const wet = rows.find((r) => r.fieldId === "f-wet");
    expect([wet?.verdict, wet?.freshness, wet?.syncStatus, wet?.deviceSerial]).toEqual([
      "wet",
      "late",
      "pending",
      "SA92-d-wet",
    ]);
  });

  it("parcelle sans kit : fraîcheur et kit à null", () => {
    const alone = rows.find((r) => r.fieldId === "f-ok2");
    expect([alone?.freshness, alone?.deviceId, alone?.lastSeenAt, alone?.verdict]).toEqual([
      null,
      null,
      null,
      "unknown",
    ]);
  });

  it("compte parcelles, sols secs, kits silencieux et alertes ouvertes", () => {
    expect(countOverview(rows)).toEqual({ fields: 6, dry: 1, silentKits: 1, openAlerts: 3 });
    expect(countOverview([])).toEqual({ fields: 0, dry: 0, silentKits: 0, openAlerts: 0 });
  });
});

/* ---------- Seuils ---------- */

describe("parseThresholdInt", () => {
  it.each([
    [30, 30],
    [0, 0],
    [" 45 ", 45],
    ["100", 100],
    ["1000", null],
    ["4.5", null],
    ["-3", null],
    ["", null],
    [4.5, null],
    [true, null],
    [null, null],
    [{}, null],
  ])("%j → %j", (raw, expected) => {
    expect(parseThresholdInt(raw)).toBe(expected);
  });
});

describe("thresholdsValid et validateThresholds", () => {
  it("démarrage + 5 ≤ arrêt ≤ 100 et démarrage ≥ 0", () => {
    expect(THRESHOLD_MIN_GAP).toBe(5);
    expect(thresholdsValid(30, 35)).toBe(true);
    expect(thresholdsValid(30, 34)).toBe(false);
    expect(thresholdsValid(0, 100)).toBe(true);
    expect(thresholdsValid(-1, 50)).toBe(false);
    expect(thresholdsValid(50, 101)).toBe(false);
  });

  it("renvoie la paire entière quand elle est valide", () => {
    expect(validateThresholds("30", 60)).toEqual({ ok: true, value: { start: 30, stop: 60 } });
  });

  it("signale les deux champs non entiers sans aller plus loin", () => {
    expect(validateThresholds("a", 4.5)).toEqual({
      ok: false,
      errors: [
        { field: "start", code: "not_integer" },
        { field: "stop", code: "not_integer" },
      ],
    });
  });

  it("cumule démarrage négatif, arrêt au-dessus de 100 et écart trop faible", () => {
    expect(validateThresholds(-10, 120)).toEqual({
      ok: false,
      errors: [
        { field: "start", code: "start_negative" },
        { field: "stop", code: "stop_above_max" },
      ],
    });
    expect(validateThresholds(98, 101)).toEqual({
      ok: false,
      errors: [
        { field: "stop", code: "stop_above_max" },
        { field: "stop", code: "gap_too_small" },
      ],
    });
  });
});

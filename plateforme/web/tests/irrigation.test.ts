import { describe, expect, it } from "vitest";

import type { IrrigationNeed } from "@/lib/contracts/field";
import { climaticDemand, isDegraded, readingKind } from "@/lib/irrigation";
import { MODULES } from "@/lib/modules";
import { SERVICE_SCREENS } from "@/lib/service-screens";
import type { WeatherDay } from "@/lib/types";

const day = (et0: number | null, rain: number | null): WeatherDay => ({
  date: "2026-11-09",
  t_max_c: 30,
  t_min_c: 20,
  precipitation_mm: rain,
  et0_mm: et0,
  et0_hargreaves_mm: et0,
});

const need = (over: Partial<IrrigationNeed>, stale = false): IrrigationNeed => ({
  field_id: "f",
  window_hours: 24,
  need_mm: 3,
  volume_m3: 10,
  defer: false,
  defer_reason: null,
  rain_expected_mm: 0,
  provenance: {
    model_name: "irr_need_24h",
    model_version: "3",
    source: "agriml",
    fallback_step: 0,
    computed_at: "2026-11-09T08:00:00Z",
    data_as_of: null,
    stale,
    confidence: { kind: "none", value: null, p10: null, p90: null, calibrated: false },
  },
  ...over,
});

describe("climaticDemand", () => {
  it("somme ET0 moins pluie sur les jours complets", () => {
    expect(climaticDemand([day(5, 1), day(4, 0), day(null, 3)])).toEqual({
      demandMm: 8,
      etMm: 9,
      rainMm: 1,
      daysCounted: 2,
    });
  });

  it("ramène une demande négative à 0", () => {
    expect(climaticDemand([day(2, 10)])?.demandMm).toBe(0);
  });

  it("renvoie null sans jour complet", () => {
    expect(climaticDemand([day(null, 1), day(2, null)])).toBeNull();
    expect(climaticDemand([])).toBeNull();
  });
});

describe("readingKind et isDegraded", () => {
  it("distingue abstention, report, aucun besoin et besoin", () => {
    expect(readingKind(need({ defer: true, volume_m3: null }))).toBe("abstained");
    expect(readingKind(need({ defer: true }))).toBe("deferred");
    expect(readingKind(need({ need_mm: 0 }))).toBe("none");
    expect(readingKind(need({}))).toBe("needed");
  });

  it("signale un résultat périmé", () => {
    expect(isDegraded(need({}))).toBe(false);
    expect(isDegraded(need({}, true))).toBe(true);
  });
});

describe("SERVICE_SCREENS", () => {
  it("slugs uniques et distincts des 13 modules", () => {
    const slugs = SERVICE_SCREENS.map((s) => s.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    expect(slugs.some((s) => MODULES.some((m) => m.slug === s))).toBe(false);
  });
});

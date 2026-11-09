/**
 * Périodes des courbes J/S/M/A (lib/ranges.ts) et fenêtre des rapports (lib/report-window.ts).
 */
import { describe, expect, it } from "vitest";

import { RANGES, RANGE_KEYS, rangeWindow, soilMoisture } from "@/lib/ranges";
import { DEFAULT_REPORT_DAYS, defaultDateRange, isoDay, toReportWindow } from "@/lib/report-window";

describe("rangeWindow", () => {
  const now = new Date("2026-11-09T12:34:56.789Z");

  it("arrondit la fin à la minute pour stabiliser la clé de cache", () => {
    expect(rangeWindow("day", now)).toEqual({
      from: "2026-11-08T12:34:00.000Z",
      to: "2026-11-09T12:34:00.000Z",
      bucket: "1h",
    });
  });

  it.each(RANGE_KEYS.map((key) => [key] as const))(
    "%s : durée et pas d'agrégation du tableau RANGES",
    (key) => {
      const window = rangeWindow(key, now);
      const hours = (Date.parse(window.to) - Date.parse(window.from)) / 3_600_000;
      expect(hours).toBe(RANGES[key].hours);
      expect(window.bucket).toBe(RANGES[key].bucket);
    },
  );

  it("quatre périodes dans l'ordre J, S, M, A", () => {
    expect(RANGE_KEYS).toEqual(["day", "week", "month", "year"]);
    expect([RANGES.month.bucket, RANGES.year.bucket]).toEqual(["1d", "1w"]);
  });
});

describe("soilMoisture", () => {
  it("moyenne si agrégée, valeur brute sinon, null si absente ou non finie", () => {
    expect(soilMoisture({ ts: "t", soil_moisture_pct_avg: 41, soil_moisture_pct: 12 })).toBe(41);
    expect(soilMoisture({ ts: "t", soil_moisture_pct_avg: null, soil_moisture_pct: 12 })).toBe(12);
    expect(soilMoisture({ ts: "t" })).toBeNull();
    expect(soilMoisture({ ts: "t", soil_moisture_pct: Number.NaN })).toBeNull();
  });
});

describe("fenêtre des rapports", () => {
  it("isoDay et période par défaut de 30 jours", () => {
    const now = new Date("2026-11-09T23:30:00Z");
    expect(isoDay(now)).toBe("2026-11-09");
    expect(DEFAULT_REPORT_DAYS).toBe(30);
    expect(defaultDateRange(now)).toEqual({ from: "2026-10-10", to: "2026-11-09" });
    expect(defaultDateRange(now, 7)).toEqual({ from: "2026-11-02", to: "2026-11-09" });
  });

  it("convertit en bornes UTC du premier au dernier instant", () => {
    expect(toReportWindow({ from: "2026-10-01", to: "2026-10-31" })).toEqual({
      from: "2026-10-01T00:00:00Z",
      to: "2026-10-31T23:59:59Z",
    });
    expect(toReportWindow({ from: "2026-10-01", to: "2026-10-01" })).not.toBeNull();
  });

  it.each([
    ["début après la fin", { from: "2026-11-02", to: "2026-11-01" }],
    ["format inattendu", { from: "01/10/2026", to: "2026-10-31" }],
    ["fin vide", { from: "2026-10-01", to: "" }],
    ["mois impossible", { from: "2026-13-01", to: "2026-13-02" }],
  ])("null si %s", (_label, range) => {
    expect(toReportWindow(range)).toBeNull();
  });
});

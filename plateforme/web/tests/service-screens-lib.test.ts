import { describe, expect, it } from "vitest";

import { formatMinutes, planTotals, slotMinutes, sortedSlots } from "@/lib/irrigation-plan";
import { changePct, sortedPriceHorizons } from "@/lib/prices";
import { firstBelowStart, forecastRange, soilStatus, sortedHorizons } from "@/lib/soil-forecast";
import { dailyTotals, photoCount, trapTotal, trapTrend } from "@/lib/traps";
import { gapfilledShare, indexDelta, latestIndex, seriesValues } from "@/lib/vegetation";
import { calendarWindow, dayAlignedWindow, isoDay } from "@/lib/windows";

const NOW = new Date("2027-03-02T14:35:12Z");

describe("windows", () => {
  it("aligne la fenêtre sur minuit UTC et inclut aujourd'hui", () => {
    expect(dayAlignedWindow(NOW, 14)).toEqual({
      from: "2027-02-17T00:00:00.000Z",
      to: "2027-03-03T00:00:00.000Z",
    });
  });

  it("donne la même clé quelle que soit l'heure du jour", () => {
    const later = new Date("2027-03-02T23:59:59Z");
    expect(dayAlignedWindow(later, 7)).toEqual(dayAlignedWindow(NOW, 7));
  });

  it("produit des jours calendaires bornes incluses", () => {
    expect(calendarWindow(NOW, 90)).toEqual({ from: "2026-12-03", to: "2027-03-02" });
    expect(isoDay(NOW)).toBe("2027-03-02");
  });
});

describe("soil-forecast", () => {
  const horizons = [
    { hours: 72, p10: 20, p50: 25, p90: 31 },
    { hours: 24, p10: 30, p50: 34, p90: 38 },
    { hours: 48, p10: 24, p50: 29, p90: 34 },
  ];
  const thresholds = { start_pct: 28, stop_pct: 40 };

  it("trie les horizons par durée sans modifier l'entrée", () => {
    expect(sortedHorizons(horizons).map((h) => h.hours)).toEqual([24, 48, 72]);
    expect(horizons[0]?.hours).toBe(72);
  });

  it("situe la médiane par rapport aux seuils, et se tait sans seuils", () => {
    expect(soilStatus(25, thresholds)).toBe("below_start");
    expect(soilStatus(34, thresholds)).toBe("between");
    expect(soilStatus(45, thresholds)).toBe("above_stop");
    expect(soilStatus(25, null)).toBeNull();
  });

  it("repère le premier horizon sous le seuil de démarrage", () => {
    expect(firstBelowStart(horizons, thresholds)?.hours).toBe(72);
    expect(firstBelowStart(horizons, null)).toBeNull();
    expect(firstBelowStart([], thresholds)).toBeNull();
  });

  it("résume la plage p10–p90", () => {
    expect(forecastRange(horizons)).toEqual({ low: 20, high: 38 });
    expect(forecastRange([])).toBeNull();
  });
});

describe("irrigation-plan", () => {
  const slot = (field: string, start: string, end: string, volume: number) => ({
    field_id: field,
    pump_id: "p1",
    start,
    end,
    volume_m3: volume,
  });
  const slots = [
    slot("b", "2027-03-02T07:00:00Z", "2027-03-02T08:30:00Z", 12),
    slot("a", "2027-03-02T05:00:00Z", "2027-03-02T05:45:00Z", 8),
  ];

  it("trie par heure de début", () => {
    expect(sortedSlots(slots).map((s) => s.field_id)).toEqual(["a", "b"]);
  });

  it("calcule durées et totaux", () => {
    expect(slotMinutes(slots[0]!)).toBe(90);
    expect(planTotals(slots)).toEqual({ volumeM3: 20, minutes: 135, fields: 2 });
  });

  it("ignore un créneau dont la fin précède le début", () => {
    expect(slotMinutes(slot("a", "2027-03-02T08:00:00Z", "2027-03-02T07:00:00Z", 1))).toBe(0);
  });

  it("formate les durées", () => {
    expect([formatMinutes(45), formatMinutes(120), formatMinutes(90)]).toEqual(["45 min", "2 h", "1 h 30"]);
  });
});

describe("traps", () => {
  const point = (at: string, count: number, image: string | null = null) => ({
    captured_at: at,
    count,
    image_id: image,
  });

  it("additionne par jour dans l'ordre chronologique", () => {
    const series = [
      point("2027-03-02T06:00:00Z", 3),
      point("2027-03-01T06:00:00Z", 1),
      point("2027-03-01T18:00:00Z", 2, "img-1"),
    ];
    expect(dailyTotals(series)).toEqual([
      { day: "2027-03-01", count: 3 },
      { day: "2027-03-02", count: 3 },
    ]);
    expect(trapTotal(series)).toBe(6);
    expect(photoCount(series)).toBe(1);
  });

  it("détecte la tendance sans conclure sur trop peu de jours", () => {
    expect(trapTrend([{ count: 1 }, { count: 1 }, { count: 5 }, { count: 6 }])).toBe("up");
    expect(trapTrend([{ count: 6 }, { count: 6 }, { count: 2 }, { count: 1 }])).toBe("down");
    expect(trapTrend([{ count: 4 }, { count: 4 }, { count: 4 }, { count: 4 }])).toBe("flat");
    expect(trapTrend([{ count: 0 }, { count: 0 }, { count: 0 }, { count: 0 }])).toBe("flat");
    expect(trapTrend([{ count: 1 }, { count: 9 }])).toBeNull();
  });
});

describe("vegetation", () => {
  const series = [
    { date: "2027-02-01", ndvi: 0.4, evi: 0.2, gapfilled: false },
    { date: "2027-02-08", ndvi: 0.5, evi: null, gapfilled: true },
    { date: "2027-02-15", ndvi: null, evi: null, gapfilled: true },
  ];

  it("retient le dernier point renseigné pour chaque indice", () => {
    expect(latestIndex(series, "ndvi")?.date).toBe("2027-02-08");
    expect(latestIndex(series, "evi")?.date).toBe("2027-02-01");
    expect(latestIndex([], "ndvi")).toBeNull();
  });

  it("calcule l'écart sur les valeurs non nulles", () => {
    expect(indexDelta(series, "ndvi")).toBeCloseTo(0.1);
    expect(indexDelta(series, "evi")).toBeNull();
  });

  it("dit la part de points reconstitués", () => {
    expect(gapfilledShare(series)).toBeCloseTo(2 / 3);
    expect(gapfilledShare([])).toBeNull();
    expect(seriesValues(series, "ndvi")).toEqual([0.4, 0.5, null]);
  });
});

describe("prices", () => {
  it("trie les semaines et mesure l'écart à l'observation", () => {
    const sorted = sortedPriceHorizons([
      { weeks: 3, p10: 1, p50: 2, p90: 3 },
      { weeks: 1, p10: 1, p50: 2, p90: 3 },
    ]);
    expect(sorted.map((h) => h.weeks)).toEqual([1, 3]);
    expect(changePct(200, 210)).toBe(5);
    expect(changePct(200, 180)).toBe(-10);
    expect(changePct(null, 180)).toBeNull();
    expect(changePct(0, 180)).toBeNull();
  });
});

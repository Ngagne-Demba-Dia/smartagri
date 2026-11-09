/**
 * Formats d'affichage (lib/format.ts) : français du Sénégal, heure de Dakar, tiret pour toute valeur absente.
 * Les séparateurs de milliers d'Intl sont des espaces insécables : comparés avec \s.
 */
import { describe, expect, it } from "vitest";

import {
  MISSING,
  formatClock,
  formatDate,
  formatDateTime,
  formatNumber,
  formatPct,
  formatWeekday,
  parseIso,
  relativeAge,
} from "@/lib/format";

/** Espace insécable (U+00A0) avant « % » et autour de « h », comme en typographie française. */
const NBSP = " ";

describe("parseIso", () => {
  it("lit une date ISO ; null pour vide, absent ou illisible", () => {
    expect(parseIso("2026-11-09T09:05:00Z")?.toISOString()).toBe("2026-11-09T09:05:00.000Z");
    expect(parseIso(null)).toBeNull();
    expect(parseIso(undefined)).toBeNull();
    expect(parseIso("")).toBeNull();
    expect(parseIso("pas une date")).toBeNull();
  });
});

describe("formatNumber et formatPct", () => {
  it("virgule décimale et espace de milliers ; arrondi selon maxDigits", () => {
    expect(formatNumber(1234.56, 1)).toMatch(/^1\s234,6$/u);
    expect(formatNumber(42.4)).toBe("42");
    expect(formatNumber(0)).toBe("0");
  });

  it.each([null, undefined, Number.NaN, Number.POSITIVE_INFINITY])(
    "valeur absente ou non finie (%s) → tiret",
    (value) => {
      expect(formatNumber(value)).toBe(MISSING);
      expect(formatPct(value)).toBe(MISSING);
    },
  );

  it("pourcentage suivi d'une espace insécable et du signe %", () => {
    expect(formatPct(42)).toBe(`42${NBSP}%`);
    expect(formatPct(41.25, 1)).toBe(`41,3${NBSP}%`);
  });
});

describe("dates et heures (Africa/Dakar, UTC+0)", () => {
  const iso = "2026-11-09T09:05:00Z";

  it("date courte, date et heure, jour de la semaine", () => {
    expect(formatDate(iso)).toBe("9 nov. 2026");
    expect(formatDateTime(iso)).toBe(`9 nov. 2026, 9${NBSP}h${NBSP}05`);
    expect(formatWeekday(iso)).toBe("lun. 9");
  });

  it("heure à la française, sans zéro initial ; minuit compte pour 0 h", () => {
    expect(formatClock(new Date("2026-11-09T21:40:00Z"))).toBe(`21${NBSP}h${NBSP}40`);
    expect(formatClock("2026-11-09T00:00:00Z")).toBe(`0${NBSP}h${NBSP}00`);
  });

  it.each([null, undefined, "", "illisible"])("date absente ou illisible (%s) → tiret", (value) => {
    expect(formatDate(value)).toBe(MISSING);
    expect(formatDateTime(value)).toBe(MISSING);
    expect(formatClock(value)).toBe(MISSING);
    expect(formatWeekday(value)).toBe(MISSING);
  });
});

describe("relativeAge", () => {
  const now = new Date("2026-11-09T12:00:00Z");
  const ago = (ms: number) => new Date(now.getTime() - ms).toISOString();

  it.each([
    [30_000, "now", 0],
    [59_999, "now", 0],
    [60_000, "minutes", 1],
    [59 * 60_000, "minutes", 59],
    [3_600_000, "hours", 1],
    [23 * 3_600_000 + 59 * 60_000, "hours", 23],
    [86_400_000, "days", 1],
    [10 * 86_400_000, "days", 10],
  ])("%i ms → %s (%i)", (ms, unit, count) => {
    expect(relativeAge(ago(ms), now)).toEqual({ unit, count });
  });

  it("un horodatage dans le futur compte comme « à l'instant »", () => {
    expect(relativeAge("2026-11-09T13:00:00Z", now)).toEqual({ unit: "now", count: 0 });
  });

  it("null sans horodatage lisible", () => {
    expect(relativeAge(null, now)).toBeNull();
    expect(relativeAge("illisible", now)).toBeNull();
  });
});

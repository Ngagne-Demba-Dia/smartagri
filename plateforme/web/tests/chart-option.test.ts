/**
 * Description des graphiques (lib/chart-option.ts, doc 10 §5) : un seul axe, légende à partir de deux éléments,
 * points masqués au-delà de 31 catégories, bande p10–p90 jamais inventée, vue en tableau et clavier.
 */
import { describe, expect, it } from "vitest";

import {
  MAX_SYMBOLS,
  chartTableHeaders,
  chartTableRows,
  describePoint,
  legendVisible,
  nextPointer,
  seriesColor,
  showDots,
  toChartRows,
  yDomain,
  type ChartSpec,
} from "@/lib/chart-option";

const spec: ChartSpec = {
  categories: ["lun.", "mar.", "mer."],
  series: [{ id: "yield", name: "Rendement", kind: "line", values: [10, null, 12] }],
  unit: "t/ha",
  summary: "Rendement prévu sur trois semaines",
};

const withBand: ChartSpec = {
  ...spec,
  band: { id: "p10p90", name: "Intervalle", low: [8, 9, null], high: [12, 13, 14] },
};

const format = (value: number | null) => (value === null ? "—" : String(value));

describe("règles d'affichage", () => {
  it("couleurs dans l'ordre fixe, encre atténuée au-delà de la palette", () => {
    expect([seriesColor(0), seriesColor(1), seriesColor(2)]).toEqual([
      "var(--series-1)",
      "var(--series-2)",
      "var(--mute)",
    ]);
  });

  it("légende seulement à partir de deux éléments nommés", () => {
    expect(legendVisible(spec)).toBe(false);
    expect(legendVisible(withBand)).toBe(true);
    expect(
      legendVisible({ ...spec, series: [...spec.series, { id: "b", name: "B", kind: "bar", values: [] }] }),
    ).toBe(true);
  });

  it("points dessinés jusqu'à 31 catégories", () => {
    const categories = (n: number) => Array.from({ length: n }, (_, i) => `j${i}`);
    expect(MAX_SYMBOLS).toBe(31);
    expect(showDots({ ...spec, categories: categories(31) })).toBe(true);
    expect(showDots({ ...spec, categories: categories(32) })).toBe(false);
  });

  it("domaine Y automatique sauf bornes fournies", () => {
    expect(yDomain(spec)).toEqual(["auto", "auto"]);
    expect(yDomain({ ...spec, yMin: 0, yMax: 100 })).toEqual([0, 100]);
  });
});

describe("données", () => {
  it("une ligne par catégorie ; la bande en [bas, haut] ou null si une borne manque", () => {
    expect(toChartRows(spec)).toEqual([
      { category: "lun.", yield: 10 },
      { category: "mar.", yield: null },
      { category: "mer.", yield: 12 },
    ]);
    expect(toChartRows(withBand).map((row) => row.p10p90)).toEqual([[8, 12], [9, 13], null]);
  });

  it("une valeur manquante en fin de série devient null", () => {
    expect(
      toChartRows({ ...spec, series: [{ ...spec.series[0]!, values: [1] }] }).map((r) => r.yield),
    ).toEqual([1, null, null]);
  });

  it("vue en tableau : en-têtes avec unité, bornes de la bande en colonnes", () => {
    const labels = { low: "bas", high: "haut" };
    expect(chartTableHeaders(spec, labels)).toEqual(["Rendement (t/ha)"]);
    expect(chartTableHeaders(withBand, labels)).toEqual([
      "Rendement (t/ha)",
      "Intervalle — bas (t/ha)",
      "Intervalle — haut (t/ha)",
    ]);
    expect(chartTableRows(spec)[1]).toEqual({ category: "mar.", values: [null] });
    expect(chartTableRows(withBand)[2]).toEqual({ category: "mer.", values: [12, null, 14] });
  });

  it("phrase annoncée au clavier, bande comprise quand ses deux bornes existent", () => {
    expect(describePoint(withBand, 0, format)).toBe("lun. : Rendement 10, Intervalle 8 – 12");
    expect(describePoint(withBand, 2, format)).toBe("mer. : Rendement 12");
    expect(describePoint(spec, 1, format)).toBe("mar. : Rendement —");
    expect(describePoint(spec, 9, format)).toBe(" : Rendement —");
  });
});

describe("nextPointer", () => {
  it.each([
    [0, "ArrowRight", 1],
    [2, "ArrowRight", 2],
    [1, "ArrowLeft", 0],
    [0, "ArrowLeft", 0],
    [1, "Home", 0],
    [0, "End", 2],
    [-1, "ArrowRight", 0],
    [-1, "ArrowLeft", 2],
    [-1, "End", 2],
  ])("depuis %i, %s → %i (3 points)", (current, key, expected) => {
    expect(nextPointer(current, key, 3)).toBe(expected);
  });

  it("null pour une touche non gérée ou sans point", () => {
    expect(nextPointer(0, "Enter", 3)).toBeNull();
    expect(nextPointer(0, "ArrowRight", 0)).toBeNull();
  });
});

/** Végétation (service 11) : NDVI/EVI issus de la télédétection, dernière valeur et tendance. */
import type { Vegetation } from "./contracts/field";

export type VegetationPoint = Vegetation["series"][number];
export type Index = "ndvi" | "evi";

/** Dernier point portant une valeur pour l'indice ; null si la série n'en a aucune. */
export function latestIndex(series: readonly VegetationPoint[], index: Index): VegetationPoint | null {
  for (let i = series.length - 1; i >= 0; i -= 1) {
    const point = series[i];
    if (point && point[index] !== null) return point;
  }
  return null;
}

/** Écart entre la dernière valeur et la précédente (points non nuls) ; null sous deux valeurs. */
export function indexDelta(series: readonly VegetationPoint[], index: Index): number | null {
  const values = series.map((p) => p[index]).filter((v): v is number => v !== null);
  const last = values[values.length - 1];
  const before = values[values.length - 2];
  return last === undefined || before === undefined ? null : last - before;
}

/** Part de points reconstitués (nuages) : à dire, car ces valeurs sont interpolées. */
export function gapfilledShare(series: readonly VegetationPoint[]): number | null {
  if (series.length === 0) return null;
  return series.filter((p) => p.gapfilled).length / series.length;
}

export function seriesValues(series: readonly VegetationPoint[], index: Index): Array<number | null> {
  return series.map((p) => p[index]);
}

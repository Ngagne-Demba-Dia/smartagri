"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Chart } from "@/components/chart/Chart";
import { QueryState } from "@/components/QueryState";
import { useMeasurements } from "@/hooks/devices";
import type { ChartSpec, ValueFormatter } from "@/lib/chart-option";
import { formatClock, formatDate, formatPct, formatWeekday } from "@/lib/format";
import { RANGE_KEYS, soilMoisture, type RangeKey } from "@/lib/ranges";
import type { SeriesRow, ThresholdPair } from "@/lib/types";

const formatMoisture: ValueFormatter = (value) => formatPct(value, 1);

const CATEGORY_LABEL: Record<RangeKey, (ts: string) => string> = {
  day: (ts) => formatClock(ts),
  week: (ts) => `${formatWeekday(ts)} ${formatClock(ts)}`,
  month: (ts) => formatDate(ts),
  year: (ts) => formatDate(ts),
};

function extent(values: ReadonlyArray<number | null>): { min: number; max: number } | null {
  const present = values.filter((v): v is number => v !== null);
  return present.length === 0 ? null : { min: Math.min(...present), max: Math.max(...present) };
}

/** Courbe d'humidité du sol J/S/M/A avec les seuils voulus en lignes pointillées (doc 10, module 3). */
export function MoistureChart({
  deviceId,
  thresholds,
}: {
  deviceId: string;
  thresholds: ThresholdPair | null;
}) {
  const t = useTranslations("moisture");
  const [range, setRange] = useState<RangeKey>("week");
  const series = useMeasurements(deviceId, range);

  const spec = useMemo<ChartSpec | null>(() => {
    const rows: readonly SeriesRow[] = series.data?.rows ?? [];
    if (rows.length === 0) return null;
    const values = rows.map(soilMoisture);
    const span = extent(values);
    const rangeLabel = t(`range.${range}`);
    return {
      categories: rows.map((r) => CATEGORY_LABEL[range](r.ts)),
      series: [{ id: "soil", name: t("series"), kind: "line", values }],
      unit: "%",
      yMin: 0,
      yMax: 100,
      references: thresholds
        ? [
            { value: thresholds.start_pct, label: t("start", { value: thresholds.start_pct }) },
            { value: thresholds.stop_pct, label: t("stop", { value: thresholds.stop_pct }) },
          ]
        : [],
      summary: span
        ? t("summary", { range: rangeLabel, min: formatMoisture(span.min), max: formatMoisture(span.max) })
        : t("summaryEmpty", { range: rangeLabel }),
    };
  }, [series.data, range, thresholds, t]);

  return (
    <section className="flex flex-col gap-2" aria-labelledby="moisture-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="moisture-title" className="text-lg font-semibold">
          {t("title")}
        </h2>
        <div role="group" aria-label={t("rangeLabel")} className="flex gap-1">
          {RANGE_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              className={key === range ? "btn-primary" : "btn-secondary"}
              aria-pressed={key === range}
              onClick={() => setRange(key)}
            >
              {t(`rangeShort.${key}`)}
            </button>
          ))}
        </div>
      </div>
      <QueryState
        isPending={series.isPending}
        error={series.error}
        isEmpty={spec === null}
        emptyLabel={t("empty")}
        onRetry={() => void series.refetch()}
      >
        {spec ? (
          <Chart
            title={t("chartTitle", { range: t(`range.${range}`) })}
            spec={spec}
            formatValue={formatMoisture}
          />
        ) : null}
      </QueryState>
    </section>
  );
}

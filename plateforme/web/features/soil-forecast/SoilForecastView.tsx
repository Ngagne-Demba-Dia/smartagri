"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { AiCard } from "@/components/AiCard";
import { Chart } from "@/components/chart/Chart";
import { FieldPicker } from "@/components/FieldPicker";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { useAllFields } from "@/hooks/places";
import type { ChartSpec, ValueFormatter } from "@/lib/chart-option";
import type { SoilForecast } from "@/lib/contracts/field";
import { formatDateTime, formatNumber, formatPct } from "@/lib/format";
import {
  firstBelowStart,
  forecastRange,
  soilStatus,
  sortedHorizons,
  type SoilStatus,
} from "@/lib/soil-forecast";
import type { Tone } from "@/lib/status";
import { useSoilForecast } from "@/services/ai/soil-forecast";

const STATUS_TONE: Record<SoilStatus, Tone> = { below_start: "warn", between: "ok", above_stop: "info" };

const formatPoint: ValueFormatter = (v) => (v === null ? formatNumber(v) : formatPct(v, 1));

function useSoilChart(forecast: SoilForecast): ChartSpec | null {
  const t = useTranslations("soilForecast");
  return useMemo(() => {
    const horizons = sortedHorizons(forecast.horizons);
    const range = forecastRange(horizons);
    if (!range) return null;
    const references = forecast.thresholds
      ? [
          { value: forecast.thresholds.start_pct, label: t("startLine") },
          { value: forecast.thresholds.stop_pct, label: t("stopLine") },
        ]
      : [];
    return {
      categories: horizons.map((h) => t("horizon", { hours: h.hours })),
      series: [{ id: "p50", name: t("median"), kind: "line", values: horizons.map((h) => h.p50) }],
      band: {
        id: "p10p90",
        name: t("band"),
        low: horizons.map((h) => h.p10),
        high: horizons.map((h) => h.p90),
      },
      references,
      unit: "%",
      summary: t("chartSummary", {
        count: horizons.length,
        low: formatPct(range.low, 1),
        high: formatPct(range.high, 1),
      }),
    } satisfies ChartSpec;
  }, [forecast, t]);
}

function Alert({ forecast }: { forecast: SoilForecast }) {
  const t = useTranslations("soilForecast");
  const thresholds = forecast.thresholds;
  if (!thresholds) return <p className="text-mute">{t("noThresholds")}</p>;
  const start = formatPct(thresholds.start_pct, 1);
  const crossing = firstBelowStart(forecast.horizons, thresholds);
  return (
    <p role="status" className="font-semibold">
      {crossing ? t("alertBelow", { start, hours: crossing.hours }) : t("alertOk", { start })}
    </p>
  );
}

function Result({ forecast }: { forecast: SoilForecast }) {
  const t = useTranslations("soilForecast");
  const chart = useSoilChart(forecast);
  const horizons = sortedHorizons(forecast.horizons);
  return (
    <AiCard title={t("cardTitle")} provenance={forecast.provenance} unit=" %">
      <div className="flex flex-col gap-4">
        <Alert forecast={forecast} />
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {horizons.map((h) => {
            const status = soilStatus(h.p50, forecast.thresholds);
            return (
              <KpiCard
                key={h.hours}
                label={t("horizon", { hours: h.hours })}
                value={formatNumber(h.p50, 1)}
                unit="%"
                hint={t("range", { low: formatPct(h.p10, 1), high: formatPct(h.p90, 1) })}
              >
                {status ? <StatusTag tone={STATUS_TONE[status]} label={t(`status.${status}`)} /> : null}
              </KpiCard>
            );
          })}
        </dl>
        {chart ? <Chart title={t("chartTitle")} spec={chart} formatValue={formatPoint} /> : null}
        <p className="text-sm text-mute">{t("issuedAt", { when: formatDateTime(forecast.issued_at) })}</p>
      </div>
    </AiCard>
  );
}

/** Humidité prévue (service 2, doc 18) : médiane et plage p10–p90 à 24, 48 et 72 h, situées par rapport aux seuils du kit. */
export function SoilForecastView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("soilForecast");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const query = useSoilForecast(fieldId);

  return (
    <ModuleShell title={tm("soilForecast")} description={t("description")} version="MVP">
      <QueryState
        isPending={all.isPending}
        error={all.error}
        isEmpty={all.fields.length === 0}
        emptyLabel={t("noFields")}
        onRetry={all.refetch}
      >
        <FieldPicker farms={all.farms} fields={all.fields} value={fieldId} onChange={setFieldId} />
        {fieldId ? (
          <QueryState
            isPending={query.isPending}
            error={query.error}
            isEmpty={!query.data || query.data.horizons.length === 0}
            emptyLabel={t("empty")}
            onRetry={() => void query.refetch()}
          >
            {query.data ? <Result forecast={query.data} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

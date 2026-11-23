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
import type { YieldForecast } from "@/lib/contracts/field";
import { MISSING, formatDate, formatNumber } from "@/lib/format";
import { useYieldForecast } from "@/services/ai/yield-forecast";

type Forecast = NonNullable<YieldForecast["forecast"]>;

const formatTons: ValueFormatter = (v) => formatNumber(v, 1);
const tons = (v: number | null) => (v === null ? MISSING : `${formatNumber(v, 1)} t/ha`);

function useYieldChart(forecast: Forecast, actual: number | null): ChartSpec {
  const t = useTranslations("yield");
  return useMemo(
    () =>
      ({
        categories: [t("low"), t("mid"), t("high")],
        series: [
          {
            id: "yield",
            name: t("cardTitle"),
            kind: "bar",
            values: [forecast.p10, forecast.predicted_t_ha, forecast.p90],
          },
        ],
        unit: "t/ha",
        yMin: 0,
        references: actual === null ? [] : [{ value: actual, label: t("actualRef") }],
        summary: t("chartSummary", {
          p10: formatNumber(forecast.p10, 1),
          p50: formatNumber(forecast.predicted_t_ha, 1),
          p90: formatNumber(forecast.p90, 1),
        }),
      }) satisfies ChartSpec,
    [forecast, actual, t],
  );
}

function ForecastResult({ view, forecast }: { view: YieldForecast; forecast: Forecast }) {
  const t = useTranslations("yield");
  const chart = useYieldChart(forecast, view.actual_t_ha);
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label={t("predicted")} value={tons(forecast.predicted_t_ha)} icon="trend" />
        <KpiCard
          label={t("interval")}
          value={t("intervalValue", { p10: tons(forecast.p10), p90: tons(forecast.p90) })}
          hint={t("intervalHelp")}
        />
        <KpiCard
          label={t("actual")}
          value={tons(view.actual_t_ha)}
          hint={view.actual_t_ha === null ? t("noActual") : undefined}
        />
        <KpiCard label={t("model")} value={`${forecast.model_name} ${forecast.model_version}`} />
      </dl>
      <Chart title={t("chartTitle")} spec={chart} formatValue={formatTons} />
    </div>
  );
}

function Result({ view }: { view: YieldForecast }) {
  const t = useTranslations("yield");
  return (
    <AiCard title={t("cardTitle")} provenance={view.provenance} unit=" t/ha">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold">
            {t("cycle", { crop: view.crop_cycle.crop, date: formatDate(view.crop_cycle.planted_on) })}
          </p>
          <StatusTag tone="warn" label={t("experimental")} />
        </div>
        {view.forecast ? (
          <ForecastResult view={view} forecast={view.forecast} />
        ) : (
          <p className="text-mute">{t("noForecast")}</p>
        )}
        <p className="text-sm text-mute">{view.caveat}</p>
      </div>
    </AiCard>
  );
}

/** Rendement (module 9, V3, expérimental) : prévision de la récolte en cours de la parcelle choisie. */
export function YieldView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("yield");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const forecast = useYieldForecast(fieldId);

  return (
    <ModuleShell title={tm("yield")} description={t("description")} version="MVP">
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
            isPending={forecast.isPending}
            error={forecast.error}
            onRetry={() => void forecast.refetch()}
          >
            {forecast.data ? <Result view={forecast.data} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

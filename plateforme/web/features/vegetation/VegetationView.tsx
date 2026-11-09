"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { AiCard } from "@/components/AiCard";
import { Chart } from "@/components/chart/Chart";
import { FieldPicker } from "@/components/FieldPicker";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { Segmented } from "@/components/Segmented";
import { useAllFields } from "@/hooks/places";
import type { ChartSpec, ValueFormatter } from "@/lib/chart-option";
import type { Vegetation } from "@/lib/contracts/field";
import { formatDate, formatNumber, formatPct } from "@/lib/format";
import { gapfilledShare, indexDelta, latestIndex, seriesValues } from "@/lib/vegetation";
import { calendarWindow } from "@/lib/windows";
import { useVegetation } from "@/services/ai/vegetation";

type Span = "30" | "60" | "90";

const formatIndex: ValueFormatter = (v) => formatNumber(v, 2);

function signed(value: number): string {
  return `${value > 0 ? "+" : ""}${formatNumber(value, 2)}`;
}

function useVegetationChart(data: Vegetation): ChartSpec {
  const t = useTranslations("vegetation");
  return useMemo(() => {
    const first = data.series[0]?.date;
    const last = data.series[data.series.length - 1]?.date;
    return {
      categories: data.series.map((p) => formatDate(p.date)),
      series: [
        { id: "ndvi", name: t("ndvi"), kind: "line", values: seriesValues(data.series, "ndvi") },
        { id: "evi", name: t("evi"), kind: "line", values: seriesValues(data.series, "evi") },
      ],
      unit: "",
      yMin: 0,
      yMax: 1,
      summary: t("chartSummary", {
        count: data.series.length,
        from: formatDate(first),
        to: formatDate(last),
      }),
    } satisfies ChartSpec;
  }, [data, t]);
}

function Result({ data }: { data: Vegetation }) {
  const t = useTranslations("vegetation");
  const chart = useVegetationChart(data);
  const ndvi = latestIndex(data.series, "ndvi");
  const evi = latestIndex(data.series, "evi");
  const ndviDelta = indexDelta(data.series, "ndvi");
  const eviDelta = indexDelta(data.series, "evi");
  const share = gapfilledShare(data.series);
  return (
    <AiCard title={t("cardTitle")} provenance={data.provenance}>
      <div className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard
            label={t("kpiNdvi")}
            value={formatNumber(ndvi?.ndvi, 2)}
            hint={ndvi ? t("latest", { date: formatDate(ndvi.date) }) : undefined}
          >
            {ndviDelta !== null ? (
              <span className="text-xs text-mute">{t("delta", { value: signed(ndviDelta) })}</span>
            ) : null}
          </KpiCard>
          <KpiCard
            label={t("kpiEvi")}
            value={formatNumber(evi?.evi, 2)}
            hint={evi ? t("latest", { date: formatDate(evi.date) }) : undefined}
          >
            {eviDelta !== null ? (
              <span className="text-xs text-mute">{t("delta", { value: signed(eviDelta) })}</span>
            ) : null}
          </KpiCard>
          <KpiCard label={t("kpiCanopy")} value={formatPct(data.canopy_cover_pct, 0)} />
          <KpiCard
            label={t("kpiStage")}
            value={data.stage ? data.stage.label : t("noStage")}
            hint={data.stage ? t("bbch", { code: data.stage.bbch }) : undefined}
          />
        </dl>
        <p className="text-sm text-mute">{t("indexHelp")}</p>
        <Chart title={t("chartTitle")} spec={chart} formatValue={formatIndex} />
        {share !== null && share > 0 ? (
          <p className="text-sm text-mute">{t("gapfilled", { share: formatPct(share * 100, 0) })}</p>
        ) : null}
      </div>
    </AiCard>
  );
}

/** Végétation (service 11, doc 18) : NDVI et EVI par satellite, couvert végétal et stade de la culture. */
export function VegetationView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("vegetation");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const [span, setSpan] = useState<Span>("90");
  const [now] = useState(() => new Date());
  const { from, to } = calendarWindow(now, Number(span));
  const query = useVegetation(fieldId, from, to);

  return (
    <ModuleShell title={tm("vegetation")} description={t("description")} version="V2">
      <QueryState
        isPending={all.isPending}
        error={all.error}
        isEmpty={all.fields.length === 0}
        emptyLabel={t("noFields")}
        onRetry={all.refetch}
      >
        <div className="flex flex-wrap items-end gap-4">
          <FieldPicker farms={all.farms} fields={all.fields} value={fieldId} onChange={setFieldId} />
          <Segmented
            legend={t("windowLegend")}
            value={span}
            onChange={setSpan}
            options={[
              { value: "30", label: t("days30") },
              { value: "60", label: t("days60") },
              { value: "90", label: t("days90") },
            ]}
          />
        </div>
        {fieldId ? (
          <QueryState
            isPending={query.isPending}
            error={query.error}
            isEmpty={!query.data || query.data.series.length === 0}
            emptyLabel={t("empty")}
            onRetry={() => void query.refetch()}
          >
            {query.data ? <Result data={query.data} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

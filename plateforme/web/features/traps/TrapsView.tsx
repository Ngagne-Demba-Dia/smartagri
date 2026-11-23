"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { AiCard } from "@/components/AiCard";
import { Chart } from "@/components/chart/Chart";
import { StickyTrapArt } from "@/components/Illustrations";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { Segmented } from "@/components/Segmented";
import { useDevices } from "@/hooks/devices";
import type { ChartSpec, ValueFormatter } from "@/lib/chart-option";
import type { TrapCounts } from "@/lib/contracts/device";
import { formatNumber, formatWeekday } from "@/lib/format";
import { dailyTotals, photoCount, trapTotal, trapTrend } from "@/lib/traps";
import { dayAlignedWindow } from "@/lib/windows";
import { DevicePicker } from "@/features/kit/DevicePicker";
import { useTrapCounts } from "@/services/ai/trap-counts";

type Span = "7" | "14" | "30";

const formatCount: ValueFormatter = (v) => formatNumber(v);

function Result({ counts }: { counts: TrapCounts }) {
  const t = useTranslations("traps");
  const tp = useTranslations("pestRisk");
  const days = useMemo(() => dailyTotals(counts.series), [counts.series]);
  const total = trapTotal(counts.series);
  const trend = trapTrend(days);
  const name = tp.has(`organisms.${counts.pest_code}.name`)
    ? tp(`organisms.${counts.pest_code}.name`)
    : counts.pest_code;
  const chart: ChartSpec = {
    categories: days.map((d) => formatWeekday(d.day)),
    series: [{ id: "count", name: t("series"), kind: "bar", values: days.map((d) => d.count) }],
    unit: "",
    yMin: 0,
    summary: t("chartSummary", { days: days.length, total: formatNumber(total) }),
  };
  return (
    <AiCard title={t("cardTitle")} provenance={counts.provenance}>
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3">
          <StickyTrapArt size={56} />
          <p className="text-sm text-mute">{t("organism", { name })}</p>
        </div>
        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <KpiCard label={t("kpiTotal")} value={formatNumber(total)} />
          <KpiCard
            label={t("kpiPerDay")}
            value={days.length > 0 ? formatNumber(total / days.length, 1) : formatNumber(null)}
          />
          <KpiCard label={t("kpiPhotos")} value={formatNumber(photoCount(counts.series))} />
          <KpiCard
            label={t("kpiTrend")}
            value={t(`trend.${trend ?? "none"}`)}
            hint={trend ? t("trendHint") : undefined}
          />
        </dl>
        <Chart title={t("chartTitle")} spec={chart} formatValue={formatCount} />
        <p className="text-sm text-mute">{t("caveat")}</p>
      </div>
    </AiCard>
  );
}

/** Pièges à insectes (service 10, doc 18) : captures comptées sur les photos du piège d'un kit. */
export function TrapsView({ initialDeviceId }: { initialDeviceId: string | null }) {
  const t = useTranslations("traps");
  const tm = useTranslations("modules");
  const devices = useDevices();
  const [selected, setSelected] = useState<string | null>(initialDeviceId);
  const [span, setSpan] = useState<Span>("14");
  const [now] = useState(() => new Date());
  const list = devices.data ?? [];
  const deviceId =
    selected !== null && list.some((d) => d.id === selected) ? selected : (list[0]?.id ?? null);
  const { from, to } = dayAlignedWindow(now, Number(span));
  const query = useTrapCounts(deviceId, from, to);

  return (
    <ModuleShell title={tm("traps")} description={t("description")} version="MVP">
      <QueryState
        isPending={devices.isPending}
        error={devices.error}
        isEmpty={list.length === 0}
        emptyLabel={t("noDevices")}
        onRetry={() => void devices.refetch()}
      >
        <div className="flex flex-wrap items-end gap-4">
          <DevicePicker devices={list} value={deviceId} onChange={setSelected} />
          <Segmented
            legend={t("windowLegend")}
            value={span}
            onChange={setSpan}
            options={[
              { value: "7", label: t("days7") },
              { value: "14", label: t("days14") },
              { value: "30", label: t("days30") },
            ]}
          />
        </div>
        {deviceId ? (
          <QueryState
            isPending={query.isPending}
            error={query.error}
            isEmpty={!query.data || query.data.series.length === 0}
            emptyLabel={t("empty")}
            onRetry={() => void query.refetch()}
          >
            {query.data ? <Result counts={query.data} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

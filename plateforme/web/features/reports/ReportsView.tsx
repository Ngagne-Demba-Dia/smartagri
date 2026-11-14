"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { exportCsvUrl, useKpis, type ReportWindow } from "@/services/ai/water-savings";
import { MISSING, formatNumber, formatPct } from "@/lib/format";
import { defaultDateRange, toReportWindow, type DateRange } from "@/lib/report-window";
import type { Kpis } from "@/lib/types";

interface CountRow {
  key: string;
  count: number;
}

function toRows(counts: Readonly<Record<string, number | undefined>>): CountRow[] {
  return Object.entries(counts)
    .filter((entry): entry is [string, number] => typeof entry[1] === "number")
    .map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count);
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="card flex min-w-0 flex-col gap-1">
      <dt className="break-words text-sm text-mute">{label}</dt>
      <dd className="break-words text-2xl font-bold tabular-nums">{value}</dd>
    </div>
  );
}

function KpiTiles({ kpis }: { kpis: Kpis }) {
  const t = useTranslations("reports");
  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Tile label={t("kpi.fields")} value={formatNumber(kpis.fields)} />
      <Tile label={t("kpi.devices")} value={formatNumber(kpis.devices)} />
      <Tile label={t("kpi.uptime")} value={formatPct(kpis.kit_uptime_pct)} />
      <Tile label={t("kpi.measurements")} value={formatNumber(kpis.measurements)} />
      <Tile label={t("kpi.irrigationEvents")} value={formatNumber(kpis.irrigation_events)} />
      <Tile label={t("kpi.pumpHours")} value={`${formatNumber(kpis.pump_hours, 1)} h`} />
      <Tile
        label={t("kpi.water")}
        value={kpis.water_m3 === null ? MISSING : `${formatNumber(kpis.water_m3, 1)} m³`}
      />
      <Tile label={t("kpi.followed")} value={formatPct(kpis.recommendations_followed_pct)} />
    </dl>
  );
}

function CountTable({
  caption,
  labelHeader,
  counts,
  label,
}: {
  caption: string;
  labelHeader: string;
  counts: Readonly<Record<string, number | undefined>>;
  label: (key: string) => string;
}) {
  const t = useTranslations("reports");
  const rows = toRows(counts);
  const columns: ReadonlyArray<Column<CountRow>> = [
    { key: "key", header: labelHeader, cell: (r) => label(r.key) },
    { key: "count", header: t("columns.count"), cell: (r) => formatNumber(r.count), numeric: true },
  ];
  if (rows.length === 0) return <p className="card text-mute">{t("noneFor", { caption })}</p>;
  return <DataTable caption={caption} columns={columns} rows={rows} rowKey={(r) => r.key} />;
}

function Report({ reportWindow }: { reportWindow: ReportWindow }) {
  const t = useTranslations("reports");
  const ta = useTranslations("alerts");
  const tf = useTranslations("recommendations.feedback");
  const kpis = useKpis(reportWindow);
  const data = kpis.data?.kpis;
  return (
    <QueryState isPending={kpis.isPending} error={kpis.error} onRetry={() => void kpis.refetch()}>
      {data ? (
        <div className="flex flex-col gap-4">
          <KpiTiles kpis={data} />
          {data.devices_without_flow > 0 ? (
            <p className="text-sm text-mute">{t("noFlow", { count: data.devices_without_flow })}</p>
          ) : null}
          <CountTable
            caption={t("alertsCaption")}
            labelHeader={t("columns.rule")}
            counts={data.alerts_by_rule}
            label={(k) => (ta.has(`rules.${k}`) ? ta(`rules.${k}`) : k)}
          />
          <CountTable
            caption={t("feedbackCaption")}
            labelHeader={t("columns.feedback")}
            counts={data.recommendations_feedback}
            label={(k) =>
              k === "followed" || k === "partially_followed" || k === "ignored" || k === "not_applicable"
                ? tf(k)
                : k
            }
          />
        </div>
      ) : null}
    </QueryState>
  );
}

/** Rapports (module 13) : indicateurs de l'organisation sur une période, export CSV. */
export function ReportsView() {
  const t = useTranslations("reports");
  const tm = useTranslations("modules");
  const [range, setRange] = useState<DateRange>(() => defaultDateRange(new Date()));
  const reportWindow = useMemo(() => toReportWindow(range), [range]);

  return (
    <ModuleShell
      title={tm("reports")}
      actions={
        reportWindow ? (
          <a className="btn btn-secondary" href={exportCsvUrl(reportWindow)} download>
            {t("export")}
          </a>
        ) : null
      }
    >
      <form className="card flex flex-wrap items-end gap-4" onSubmit={(e) => e.preventDefault()}>
        <label className="flex flex-col gap-1 text-sm font-semibold">
          {t("from")}
          <input
            type="date"
            className="field-input"
            value={range.from}
            max={range.to}
            onChange={(e) => setRange((prev) => ({ ...prev, from: e.target.value }))}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold">
          {t("to")}
          <input
            type="date"
            className="field-input"
            value={range.to}
            min={range.from}
            onChange={(e) => setRange((prev) => ({ ...prev, to: e.target.value }))}
          />
        </label>
      </form>
      {reportWindow ? (
        <Report reportWindow={reportWindow} />
      ) : (
        <p role="alert" className="card font-semibold text-bad-ink">
          {t("invalidRange")}
        </p>
      )}
    </ModuleShell>
  );
}

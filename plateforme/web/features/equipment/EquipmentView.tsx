"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";

import { DataTable, type Column } from "@/components/DataTable";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { KitHealthSection } from "@/features/kit/KitHealthSection";
import { useEquipment } from "@/hooks/reports";
import { MISSING, formatDate, formatNumber } from "@/lib/format";
import { summarizeEquipment, sortedEquipment, type EquipmentSummary } from "@/lib/equipment";
import type { Locale } from "@/i18n/routing";
import { localePath } from "@/lib/nav";
import type { Tone } from "@/lib/status";
import type { Equipment, EquipmentStatus } from "@/lib/types";

const STATUS_TONE: Record<EquipmentStatus, Tone> = { ok: "ok", maintenance: "warn", out_of_service: "bad" };

function Summary({ summary }: { summary: EquipmentSummary }) {
  const t = useTranslations("equipment");
  const locale = useLocale() as Locale;
  const attention = summary.maintenance + summary.out_of_service;
  return (
    <div className="flex flex-col gap-3">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label={t("kpiTotal")} value={formatNumber(summary.total, 0)} icon="wrench" />
        <KpiCard label={t("kpiOk")} value={formatNumber(summary.ok, 0)} icon="check" />
        <KpiCard label={t("kpiMaintenance")} value={formatNumber(summary.maintenance, 0)} icon="warn" />
        <KpiCard label={t("kpiOut")} value={formatNumber(summary.out_of_service, 0)} icon="bad" />
      </dl>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p role="status" className="m-0 font-semibold">
          {attention > 0 ? t("attention", { count: attention }) : t("allGood")}
        </p>
        <Link className="btn btn-secondary" href={localePath(locale, "/kit")}>
          {t("kitLink")}
        </Link>
      </div>
    </div>
  );
}

function useColumns(): ReadonlyArray<Column<Equipment>> {
  const t = useTranslations("equipment");
  return [
    {
      key: "label",
      header: t("columns.label"),
      cell: (e) => <span className="font-semibold">{e.label}</span>,
    },
    { key: "kind", header: t("columns.kind"), cell: (e) => t(`kind.${e.kind}`) },
    { key: "serial", header: t("columns.serial"), cell: (e) => e.serial ?? MISSING },
    {
      key: "status",
      header: t("columns.status"),
      cell: (e) => <StatusTag tone={STATUS_TONE[e.status]} label={t(`status.${e.status}`)} />,
    },
    { key: "installed", header: t("columns.installed"), cell: (e) => formatDate(e.installed_at) },
    {
      key: "flow",
      header: t("columns.flow"),
      cell: (e) => (e.flow_m3h === null ? MISSING : formatNumber(e.flow_m3h, 1)),
      numeric: true,
    },
  ];
}

/** Équipements (module 10) : inventaire, état par type et santé des kits (lecture seule). */
export function EquipmentView() {
  const t = useTranslations("equipment");
  const tm = useTranslations("modules");
  const equipment = useEquipment();
  const columns = useColumns();
  const rows = equipment.data ?? [];

  return (
    <ModuleShell title={tm("equipment")} description={t("description")} version="V1_1">
      <QueryState
        isPending={equipment.isPending}
        error={equipment.error}
        isEmpty={rows.length === 0}
        emptyLabel={t("empty")}
        onRetry={() => void equipment.refetch()}
      >
        <Summary summary={summarizeEquipment(rows)} />
        <DataTable
          caption={t("caption")}
          columns={columns}
          rows={sortedEquipment(rows)}
          rowKey={(e) => e.id}
        />
      </QueryState>
      <KitHealthSection />
    </ModuleShell>
  );
}

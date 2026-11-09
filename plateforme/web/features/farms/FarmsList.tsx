"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";

import { DataTable, type Column } from "@/components/DataTable";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { useAllFields } from "@/hooks/places";
import type { Locale } from "@/i18n/routing";
import { MISSING, formatNumber } from "@/lib/format";
import { localePath } from "@/lib/nav";
import type { Farm } from "@/lib/types";

/** Exploitations (module 2) : une ligne par exploitation, avec le nombre de parcelles et un lien filtré. */
export function FarmsList() {
  const t = useTranslations("farms");
  const tm = useTranslations("modules");
  const locale = useLocale() as Locale;
  const { farms, fields, isPending, error, refetch } = useAllFields();
  const fieldCount = new Map<string, number>();
  fields.forEach((f) => fieldCount.set(f.farm_id, (fieldCount.get(f.farm_id) ?? 0) + 1));

  const columns: ReadonlyArray<Column<Farm>> = [
    { key: "name", header: t("columns.name"), cell: (f) => <span className="font-semibold">{f.name}</span> },
    { key: "region", header: t("columns.region"), cell: (f) => f.region ?? MISSING },
    { key: "commune", header: t("columns.commune"), cell: (f) => f.commune ?? MISSING },
    { key: "area", header: t("columns.area"), cell: (f) => formatNumber(f.area_ha, 2), numeric: true },
    {
      key: "fields",
      header: t("columns.fields"),
      cell: (f) => formatNumber(fieldCount.get(f.id) ?? 0),
      numeric: true,
    },
    {
      key: "link",
      header: t("columns.link"),
      cell: (f) => (
        <Link
          href={`${localePath(locale, "/parcelles")}?exploitation=${encodeURIComponent(f.id)}`}
          className="font-semibold text-g underline"
        >
          {t("seeFields")}
          <span className="sr-only"> {f.name}</span>
        </Link>
      ),
    },
  ];

  return (
    <ModuleShell title={tm("farms")} description={t("description")}>
      <QueryState
        isPending={isPending}
        error={error}
        isEmpty={farms.length === 0}
        emptyLabel={t("empty")}
        onRetry={refetch}
      >
        <dl className="grid grid-cols-2 gap-3 lg:grid-cols-3">
          <KpiCard label={t("kpiFarms")} value={formatNumber(farms.length, 0)} icon="farm" />
          <KpiCard label={t("kpiFields")} value={formatNumber(fields.length, 0)} icon="map" />
          <KpiCard
            label={t("kpiArea")}
            value={formatNumber(
              farms.reduce((sum, f) => sum + (f.area_ha ?? 0), 0),
              1,
            )}
            unit="ha"
            icon="layers"
          />
        </dl>
        <DataTable caption={tm("farms")} captionHidden columns={columns} rows={farms} rowKey={(f) => f.id} />
      </QueryState>
    </ModuleShell>
  );
}

"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";

import { DataTable, type Column } from "@/components/DataTable";
import { Icon } from "@/components/Icon";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { useAllFields } from "@/hooks/places";
import type { Locale } from "@/i18n/routing";
import { MISSING, formatNumber } from "@/lib/format";
import { waterQualityForField } from "@/lib/irrigation";
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
        <ul className="m-0 grid list-none gap-4 p-0 md:grid-cols-2 xl:grid-cols-3">
          {farms.map((f) => {
            const count = fieldCount.get(f.id) ?? 0;
            const wq = waterQualityForField(f.id);
            const farmFields = fields.filter((fl) => fl.farm_id === f.id);
            return (
              <li key={f.id} className="card flex flex-col justify-between gap-3">
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h2 className="m-0 flex items-center gap-2 text-lg font-bold text-ink">
                      <Icon name="farm" size={20} />
                      {f.name}
                    </h2>
                    <span className="chip">
                      <Icon name="layers" size={14} />
                      {formatNumber(f.area_ha, 1)} ha
                    </span>
                  </div>
                  <p className="m-0 text-sm text-mute">
                    {f.region ?? MISSING} · {f.commune ?? MISSING}
                    {f.latitude !== null && f.longitude !== null
                      ? ` (${formatNumber(Math.abs(f.latitude), 3)}° N, ${formatNumber(Math.abs(f.longitude), 3)}° O)`
                      : ""}
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    <span className="chip">
                      <Icon name="sprout" size={14} />
                      {t("cardFields", { count })}
                    </span>
                    <span className="chip">
                      <Icon name="kit" size={14} />
                      {t("cardWaterPh", { ph: formatNumber(wq.ph, 1) })}
                    </span>
                  </div>
                  {farmFields.length > 0 ? (
                    <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0 text-xs">
                      {farmFields.map((fl) => (
                        <li key={fl.id} className="rounded-btn bg-surface px-2.5 py-1 font-medium text-ink">
                          {fl.name} ({formatNumber(fl.area_ha, 1)} ha)
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2 border-t border-line pt-3">
                  <Link
                    href={`${localePath(locale, "/parcelles")}?exploitation=${encodeURIComponent(f.id)}`}
                    className="btn-secondary min-h-touch text-sm"
                  >
                    {t("seeFields")}
                  </Link>
                  <Link href={localePath(locale, "/carte")} className="btn-secondary min-h-touch text-sm">
                    <Icon name="map" size={16} />
                    {t("seeMap")}
                  </Link>
                </div>
              </li>
            );
          })}
        </ul>
        <DataTable caption={tm("farms")} captionHidden columns={columns} rows={farms} rowKey={(f) => f.id} />
      </QueryState>
    </ModuleShell>
  );
}

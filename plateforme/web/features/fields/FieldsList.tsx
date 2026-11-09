"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useMemo } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { useDevices } from "@/hooks/devices";
import { useAllFields } from "@/hooks/places";
import type { Locale } from "@/i18n/routing";
import { useFarmMaps } from "@/services/ai/map-layers";
import { MISSING, formatNumber } from "@/lib/format";
import { localePath } from "@/lib/nav";
import { buildOverview } from "@/lib/overview";
import type { Field } from "@/lib/types";

import { FieldLiveCard } from "./FieldLiveCard";

/** Parcelles (module 3) : liste de toutes les parcelles visibles, filtrable par exploitation (?exploitation=). */
export function FieldsList({ farmId }: { farmId: string | null }) {
  const t = useTranslations("fields");
  const tm = useTranslations("modules");
  const locale = useLocale() as Locale;
  const router = useRouter();
  const filterId = useId();
  const { farms, fields, isPending, error, refetch } = useAllFields();
  const farmName = new Map(farms.map((f) => [f.id, f.name]));
  const shown = farmId ? fields.filter((f) => f.farm_id === farmId) : fields;
  // Cartes « vivantes » : mêmes sources que le tableau de bord (carte de l'exploitation + kits). Si elles tardent
  // ou échouent, le tableau ci-dessous reste la liste de référence.
  const maps = useFarmMaps();
  const devices = useDevices("active");
  const live = useMemo(
    () => buildOverview(maps.maps, devices.data ?? []).filter((row) => !farmId || row.farmId === farmId),
    [maps.maps, devices.data, farmId],
  );

  // La page serveur relit ?exploitation= et renvoie le nouveau filtre ; les données restent en cache.
  const filter = (next: string) => {
    const path = localePath(locale, "/parcelles");
    router.replace(next ? `${path}?exploitation=${encodeURIComponent(next)}` : path, { scroll: false });
  };

  const columns: ReadonlyArray<Column<Field>> = [
    {
      key: "name",
      header: t("columns.name"),
      cell: (f) => (
        <Link
          href={localePath(locale, `/parcelles/${encodeURIComponent(f.id)}`)}
          className="font-semibold text-g underline"
        >
          {f.name}
        </Link>
      ),
    },
    { key: "farm", header: t("columns.farm"), cell: (f) => farmName.get(f.farm_id) ?? MISSING },
    { key: "area", header: t("columns.area"), cell: (f) => formatNumber(f.area_ha, 2), numeric: true },
    { key: "soil", header: t("columns.soil"), cell: (f) => f.soil_type ?? MISSING },
    {
      key: "irrigation",
      header: t("columns.irrigation"),
      cell: (f) => (f.irrigation_type ? t(`irrigation.${f.irrigation_type}`) : MISSING),
    },
  ];

  return (
    <ModuleShell title={tm("fields")} description={t("description")}>
      <div className="glass flex max-w-sm flex-col gap-1 p-3">
        <label htmlFor={filterId} className="text-sm font-semibold">
          {t("filter")}
        </label>
        <select
          id={filterId}
          className="field-input"
          value={farmId ?? ""}
          onChange={(e) => filter(e.target.value)}
        >
          <option value="">{t("allFarms")}</option>
          {farms.map((farm) => (
            <option key={farm.id} value={farm.id}>
              {farm.name}
            </option>
          ))}
        </select>
      </div>
      <QueryState
        isPending={isPending}
        error={error}
        isEmpty={shown.length === 0}
        emptyLabel={t("empty")}
        onRetry={refetch}
      >
        <p role="status" className="m-0 text-sm text-mute">
          {t("count", { count: shown.length })}
        </p>
        {live.length > 0 ? (
          <ul className="stagger m-0 grid list-none gap-4 p-0 md:grid-cols-2 xl:grid-cols-3">
            {live.map((row) => (
              <FieldLiveCard key={row.fieldId} row={row} />
            ))}
          </ul>
        ) : null}
        <details className="glass group p-4" open={live.length === 0}>
          <summary className="min-h-touch cursor-pointer py-2 font-semibold text-g">{t("tableView")}</summary>
          <DataTable caption={tm("fields")} captionHidden columns={columns} rows={shown} rowKey={(f) => f.id} />
        </details>
      </QueryState>
    </ModuleShell>
  );
}

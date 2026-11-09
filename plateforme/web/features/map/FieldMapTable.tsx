"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useMemo } from "react";

import { DataTable, type Column } from "@/components/DataTable";
import { RampSwatch } from "@/components/RampSwatch";
import { StatusTag } from "@/components/StatusTag";
import { TimeAgo } from "@/components/TimeAgo";
import { useAllFields } from "@/hooks/places";
import type { FarmMapEntry } from "@/services/ai/map-layers";
import type { Locale } from "@/i18n/routing";
import { MISSING, formatNumber, formatPct } from "@/lib/format";
import type { DeviceProps, FieldProps } from "@/lib/map-style";
import { localePath } from "@/lib/nav";

type FieldRow = FieldProps & { farmName: string };
type DeviceRow = DeviceProps & { farmName: string };

/** « 14,6932° N » : hémisphère en toutes lettres plutôt qu'un signe. */
function formatCoord(value: number, positive: string, negative: string): string {
  return `${formatNumber(Math.abs(value), 4)}° ${value >= 0 ? positive : negative}`;
}

/**
 * Vue tableau de la carte (module 4) : parcelles et kits de toutes les exploitations, issus de la carte de base
 * (GET /v1/farms/{id}/map). Équivalent accessible du fond Leaflet, affiché sous celui-ci (FieldMap).
 */
export function FieldMapTable({ entries }: { entries: readonly FarmMapEntry[] }) {
  const t = useTranslations("map");
  const locale = useLocale() as Locale;
  const all = useAllFields();

  const { fieldRows, deviceRows } = useMemo(() => {
    const fieldsOut: FieldRow[] = [];
    const devicesOut: DeviceRow[] = [];
    entries.forEach(({ farmName, map }) =>
      map.features.forEach((feature) => {
        const props = feature.properties;
        if (props.kind === "field") fieldsOut.push({ ...props, farmName });
        else if (props.kind === "device") devicesOut.push({ ...props, farmName });
      }),
    );
    return { fieldRows: fieldsOut, deviceRows: devicesOut };
  }, [entries]);

  const centroids = useMemo(() => new Map(all.fields.map((f) => [f.id, f.centroid])), [all.fields]);
  const fieldNames = useMemo(() => new Map(fieldRows.map((f) => [f.field_id, f.name])), [fieldRows]);

  const fieldColumns: ReadonlyArray<Column<FieldRow>> = [
    {
      key: "name",
      header: t("columns.field"),
      cell: (f) => (
        <Link
          href={localePath(locale, `/parcelles/${encodeURIComponent(f.field_id)}`)}
          className="font-semibold text-g underline"
        >
          {f.name}
        </Link>
      ),
    },
    { key: "farm", header: t("columns.farm"), cell: (f) => f.farmName },
    { key: "crop", header: t("columns.crop"), cell: (f) => f.crop ?? MISSING },
    { key: "area", header: t("columns.area"), cell: (f) => formatNumber(f.area_ha, 2), numeric: true },
    {
      key: "moisture",
      header: t("columns.moisture"),
      cell: (f) => (
        <span className="inline-flex items-center gap-2">
          <RampSwatch moisture={f.soil_moisture_pct} size="sm" />
          {formatPct(f.soil_moisture_pct)}
        </span>
      ),
    },
    {
      key: "position",
      header: t("columns.position"),
      cell: (f) => {
        const c = centroids.get(f.field_id);
        return c ? `${formatCoord(c.latitude, "N", "S")}, ${formatCoord(c.longitude, "E", "O")}` : MISSING;
      },
    },
    {
      key: "ndvi",
      header: t("columns.ndvi"),
      cell: (f) => (f.ndvi === null ? MISSING : formatNumber(f.ndvi, 2)),
      numeric: true,
    },
    { key: "alerts", header: t("columns.alerts"), cell: (f) => formatNumber(f.open_alerts), numeric: true },
  ];

  const deviceColumns: ReadonlyArray<Column<DeviceRow>> = [
    {
      key: "serial",
      header: t("columns.kit"),
      cell: (d) => <span className="font-semibold">{d.serial}</span>,
    },
    {
      key: "field",
      header: t("columns.field"),
      cell: (d) => (d.field_id ? (fieldNames.get(d.field_id) ?? MISSING) : MISSING),
    },
    { key: "moisture", header: t("columns.moisture"), cell: (d) => formatPct(d.soil_moisture_pct) },
    { key: "seen", header: t("columns.lastSeen"), cell: (d) => <TimeAgo value={d.last_seen_at} /> },
    {
      key: "position",
      header: t("columns.position"),
      cell: (d) => (d.position_estimated ? <StatusTag tone="info" label={t("estimated")} /> : t("measured")),
    },
    { key: "alerts", header: t("columns.alerts"), cell: (d) => formatNumber(d.open_alerts), numeric: true },
  ];

  return (
    <>
      <DataTable
        caption={t("fieldsCaption")}
        columns={fieldColumns}
        rows={fieldRows}
        rowKey={(f) => f.field_id}
      />
      {deviceRows.length > 0 ? (
        <DataTable
          caption={t("kitsCaption")}
          columns={deviceColumns}
          rows={deviceRows}
          rowKey={(d) => d.device_id}
        />
      ) : null}
    </>
  );
}

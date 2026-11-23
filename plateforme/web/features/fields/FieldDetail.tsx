"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useId, useState } from "react";

import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { RampSwatch } from "@/components/RampSwatch";
import { TimeAgo } from "@/components/TimeAgo";
import { useDevice, useDevices } from "@/hooks/devices";
import { useField } from "@/hooks/places";
import type { Locale } from "@/i18n/routing";
import { MISSING, formatDate, formatNumber, formatPct } from "@/lib/format";
import { localePath } from "@/lib/nav";
import type { Device, DeviceDetail, FieldDetail as FieldDetailData } from "@/lib/types";

import { MoistureChart } from "./MoistureChart";
import { PumpState } from "./PumpState";
import { ThresholdForm } from "./ThresholdForm";

function FieldFacts({ field }: { field: FieldDetailData }) {
  const t = useTranslations("field");
  const tf = useTranslations("fields");
  const cycle = field.active_cycle;
  return (
    <dl className="card grid grid-cols-2 gap-x-3 gap-y-1 text-sm md:grid-cols-4">
      <dt className="text-mute">{t("area")}</dt>
      <dd className="tabular-nums">
        {field.area_ha !== null ? `${formatNumber(field.area_ha, 2)} ha` : MISSING}
      </dd>
      <dt className="text-mute">{t("soil")}</dt>
      <dd>{field.soil_type ?? MISSING}</dd>
      <dt className="text-mute">{t("irrigation")}</dt>
      <dd>{field.irrigation_type ? tf(`irrigation.${field.irrigation_type}`) : MISSING}</dd>
      <dt className="text-mute">{t("crop")}</dt>
      <dd>
        {cycle ? `${cycle.crop}${cycle.variety ? ` (${cycle.variety})` : ""}` : t("noCrop")}
        {cycle?.planted_on ? ` · ${t("planted", { date: formatDate(cycle.planted_on) })}` : ""}
      </dd>
    </dl>
  );
}

function LatestReading({ device }: { device: DeviceDetail }) {
  const t = useTranslations("field");
  const m = device.latest_measurement;
  if (!m) return <p className="card text-mute">{t("noMeasurement")}</p>;
  return (
    <section className="card flex flex-col gap-3" aria-labelledby="latest-title">
      <h2 id="latest-title" className="text-lg font-semibold">
        {t("latest")}
      </h2>
      <div className="flex items-center gap-3">
        <RampSwatch moisture={m.soil_moisture_pct ?? null} />
        <div>
          <p className="text-2xl font-bold tabular-nums">{formatPct(m.soil_moisture_pct ?? null)}</p>
          <p className="text-sm text-mute">{t("moisture")}</p>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
        <dt className="text-mute">{t("airTemp")}</dt>
        <dd className="tabular-nums">
          {m.air_temp_c != null ? `${formatNumber(m.air_temp_c, 1)} °C` : MISSING}
        </dd>
        <dt className="text-mute">{t("airHumidity")}</dt>
        <dd className="tabular-nums">{formatPct(m.air_humidity_pct ?? null)}</dd>
        <dt className="text-mute">{t("pressure")}</dt>
        <dd className="tabular-nums">
          {m.pressure_hpa != null ? `${formatNumber(m.pressure_hpa, 0)} hPa` : MISSING}
        </dd>
        <dt className="text-mute">{t("npk")}</dt>
        <dd className="tabular-nums">
          {m.n_mgkg != null || m.p_mgkg != null || m.k_mgkg != null
            ? `${m.n_mgkg != null ? formatNumber(m.n_mgkg, 0) : MISSING} / ${m.p_mgkg != null ? formatNumber(m.p_mgkg, 0) : MISSING} / ${m.k_mgkg != null ? formatNumber(m.k_mgkg, 0) : MISSING} mg/kg`
            : MISSING}
        </dd>
        <dt className="text-mute">{t("measuredAt")}</dt>
        <dd>
          <TimeAgo value={m.ts} />
        </dd>
      </dl>
      {m.soil_sensor_ok === false ? (
        <p className="text-sm font-semibold text-bad-ink">{t("soilSensorFault")}</p>
      ) : null}
    </section>
  );
}

function KitPicker({
  devices,
  value,
  onChange,
}: {
  devices: readonly Device[];
  value: string;
  onChange: (id: string) => void;
}) {
  const t = useTranslations("field");
  const id = useId();
  if (devices.length < 2) return null;
  return (
    <div className="flex max-w-sm flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">
        {t("chooseKit")}
      </label>
      <select id={id} className="field-input" value={value} onChange={(e) => onChange(e.target.value)}>
        {devices.map((d) => (
          <option key={d.id} value={d.id}>
            {d.name ? `${d.name} (${d.serial})` : d.serial}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Détail d'une parcelle (module 3) : faits, dernière mesure, pompe, courbe d'humidité et seuils du kit choisi. */
export function FieldDetail({ fieldId }: { fieldId: string }) {
  const t = useTranslations("field");
  const tm = useTranslations("modules");
  const locale = useLocale() as Locale;
  const field = useField(fieldId);
  const devices = useDevices("active");
  const fieldDevices = (devices.data ?? []).filter((d) => d.field_id === fieldId);
  const [chosen, setChosen] = useState<string | null>(null);
  const deviceId = chosen ?? fieldDevices[0]?.id ?? null;
  const device = useDevice(deviceId);
  const query = `?parcelle=${encodeURIComponent(fieldId)}`;

  return (
    <ModuleShell
      title={field.data?.name ?? tm("fields")}
      actions={
        <Link href={localePath(locale, "/parcelles")} className="btn-secondary">
          {t("back")}
        </Link>
      }
    >
      <QueryState isPending={field.isPending} error={field.error} onRetry={() => void field.refetch()}>
        {field.data ? <FieldFacts field={field.data} /> : null}
        <nav aria-label={t("related")} className="flex flex-wrap gap-2">
          <Link href={`${localePath(locale, "/meteo")}${query}`} className="btn-secondary">
            {t("weatherLink")}
          </Link>
          <Link href={`${localePath(locale, "/recommandations")}${query}`} className="btn-secondary">
            {t("recommendationsLink")}
          </Link>
        </nav>
        <QueryState
          isPending={devices.isPending}
          error={devices.error}
          isEmpty={fieldDevices.length === 0}
          emptyLabel={t("noKit")}
          onRetry={() => void devices.refetch()}
        >
          <KitPicker devices={fieldDevices} value={deviceId ?? ""} onChange={setChosen} />
          <QueryState isPending={device.isPending} error={device.error} onRetry={() => void device.refetch()}>
            {device.data ? (
              <div className="flex flex-col gap-4">
                <div className="grid gap-3 md:grid-cols-2">
                  <LatestReading device={device.data} />
                  <PumpState measurement={device.data.latest_measurement} />
                </div>
                <MoistureChart
                  deviceId={device.data.id}
                  thresholds={device.data.thresholds?.desired ?? null}
                />
                <ThresholdForm key={device.data.id} device={device.data} />
              </div>
            ) : null}
          </QueryState>
        </QueryState>
      </QueryState>
    </ModuleShell>
  );
}

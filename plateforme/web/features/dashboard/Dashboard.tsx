"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";
import { useMemo } from "react";

import { Icon } from "@/components/Icon";
import { SkyArt } from "@/components/Illustrations";
import { KpiCard } from "@/components/KpiCard";
import { ProvenanceNote } from "@/components/Provenance";
import { ProvenanceCapsules } from "@/components/ProvenanceCapsules";
import { QueryState } from "@/components/QueryState";
import { SKY_CLASS, skyKind } from "@/components/WeatherHero";
import { FieldLiveCard } from "@/features/fields/FieldLiveCard";
import { useAlerts } from "@/services/ai/device-health";
import { useDevices } from "@/hooks/devices";
import { useFarmMaps } from "@/services/ai/map-layers";
import { useWeather } from "@/services/ai/weather";
import type { Provenance } from "@/lib/contracts/provenance";
import type { Locale } from "@/i18n/routing";
import { formatNumber, formatWeekday } from "@/lib/format";
import { localePath } from "@/lib/nav";
import { buildOverview, countOverview, type FieldOverview } from "@/lib/overview";

const FORECAST_DAYS_SHOWN = 3;
const RAIN_ICON_MM = 1;

const isRainy = (mm: number | null) => (mm ?? 0) >= RAIN_ICON_MM;

/** Synthèse de l'IA : phrases dérivées des comptages (rien d'inventé), provenance en capsules, conseil en un clic. */
function AiSummary({
  rows,
  counts,
  provenance,
}: {
  rows: readonly FieldOverview[];
  counts: ReturnType<typeof countOverview>;
  provenance: Provenance | null;
}) {
  const t = useTranslations("dashboard");
  const locale = useLocale() as Locale;
  const driest = rows.find((r) => r.verdict === "dry");
  const sentences = [
    driest ? t("summary.dry", { count: counts.dry, field: driest.name }) : null,
    counts.silentKits > 0 ? t("summary.silent", { count: counts.silentKits }) : null,
  ].filter((s): s is string => s !== null);
  return (
    <section aria-label={t("summary.label")} className="card card-ai flex max-w-2xl flex-col gap-3">
      <div className="flex items-start gap-3">
        <span className="ai-orb" aria-hidden="true">
          <Icon name="sparkles" size={20} />
        </span>
        <div className="flex min-w-0 flex-col gap-1">
          <p className="m-0 text-sm font-semibold text-g">{t("summary.label")}</p>
          <p className="m-0 text-base font-semibold text-ink sm:text-lg">
            {sentences.length > 0 ? sentences.join(" ") : t("summary.calm")}
          </p>
        </div>
      </div>
      <ProvenanceCapsules provenance={provenance} />
      <p className="m-0 text-xs text-mute">{t("summary.auto")}</p>
      <div className="flex flex-wrap gap-2">
        <Link href={localePath(locale, "/recommandations")} className="btn-ai min-h-touch">
          <Icon name="sparkles" size={16} />
          {t("adviceLink")}
        </Link>
      </div>
    </section>
  );
}

/** Météo de la parcelle la plus urgente. Masquée si le service ne répond pas (localisation absente, panne). */
function WeatherPanel({ field }: { field: FieldOverview }) {
  const t = useTranslations("dashboard");
  const weather = useWeather(field.fieldId);
  const days = weather.data?.days.slice(0, FORECAST_DAYS_SHOWN) ?? [];
  const today = days[0];
  if (!today) return null;
  const kind = skyKind(today.precipitation_mm);
  return (
    <section
      aria-label={t("weather.title", { field: field.name })}
      className={`sky reveal flex flex-col gap-3 p-5 ${SKY_CLASS[kind]}`}
    >
      <div className="pointer-events-none absolute -right-4 -top-4 opacity-95">
        <SkyArt kind={kind} size={120} />
      </div>
      <p className="relative m-0 flex items-center gap-2 text-sm font-semibold text-white">
        <Icon name={isRainy(today.precipitation_mm) ? "rain" : "sun"} size={18} />
        {t("weather.title", { field: field.name })}
      </p>
      <p className="relative m-0 text-5xl font-bold tabular-nums text-white">
        {t("weather.range", { max: formatNumber(today.t_max_c, 0), min: formatNumber(today.t_min_c, 0) })}
      </p>
      <p className="relative m-0 text-sm text-white">
        {t("weather.rain", { mm: formatNumber(today.precipitation_mm, 1) })} ·{" "}
        {t("weather.et0", { mm: formatNumber(today.et0_mm, 1) })}
      </p>
      <ul className="relative m-0 grid list-none grid-cols-3 gap-2 p-0">
        {days.map((day) => (
          <li key={day.date} className="sky-tile text-white">
            <span className="text-xs">{formatWeekday(day.date)}</span>
            <Icon name={isRainy(day.precipitation_mm) ? "rain" : "sun"} size={18} />
            <span className="text-sm font-semibold tabular-nums">{formatNumber(day.t_max_c, 0)} °</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Tableau de bord (module 1) : hero agricole avec synthèse IA et météo, chiffres clés, puis parcelles « vivantes » (doc 10 §2). */
export function Dashboard() {
  const t = useTranslations("dashboard");
  const tm = useTranslations("modules");
  const locale = useLocale() as Locale;
  const maps = useFarmMaps();
  const devices = useDevices("active");
  const alerts = useAlerts("open");

  const rows = useMemo(() => buildOverview(maps.maps, devices.data ?? []), [maps.maps, devices.data]);
  const counts = countOverview(rows);
  const critical = (alerts.data ?? []).filter((a) => a.severity === "critical").length;
  const ready = !maps.isPending && !devices.isPending && !maps.error && !devices.error && rows.length > 0;
  const lead = rows[0];

  return (
    <section className="flex flex-col gap-5" aria-labelledby="module-title">
      <header className="banner reveal">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/img/champ-hero.webp" alt="" width={1280} height={855} className="banner-img" />
        <div className="banner-scrim" />
        <div className="grid gap-6 px-5 py-6 text-white sm:px-8 sm:py-8 lg:min-h-[26rem] lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)] lg:items-end">
          <div className="flex flex-col gap-4">
            <p className="chip m-0 w-fit">
              <Icon name="sparkles" size={14} />
              {t("eyebrow")}
            </p>
            <h1 id="module-title" className="text-3xl font-bold tracking-tight sm:text-5xl">
              {tm("dashboard")}
            </h1>
            <p className="m-0 max-w-prose text-white sm:text-lg">{t("description")}</p>
            {ready ? (
              <AiSummary rows={rows} counts={counts} provenance={maps.maps[0]?.map.provenance ?? null} />
            ) : null}
          </div>
          {ready && lead ? <WeatherPanel field={lead} /> : null}
        </div>
        {ready ? (
          <dl className="stagger m-0 grid grid-cols-2 gap-3 px-5 pb-5 sm:px-8 sm:pb-8 md:grid-cols-4">
            <KpiCard label={t("kpi.fields")} value={formatNumber(counts.fields, 0)} icon="map" />
            <KpiCard label={t("kpi.dry")} value={formatNumber(counts.dry, 0)} icon="drop" />
            <KpiCard label={t("kpi.silentKits")} value={formatNumber(counts.silentKits, 0)} icon="offline" />
            <KpiCard label={t("kpi.openAlerts")} value={formatNumber(counts.openAlerts, 0)} icon="bell" />
          </dl>
        ) : null}
      </header>
      {critical > 0 ? (
        <div
          role="alert"
          className="glass flex flex-wrap items-center justify-between gap-2 !border-bad-ink !bg-bad-bg p-4 font-semibold text-bad-ink"
        >
          <span className="flex items-center gap-2">
            <Icon name="bad" size={20} />
            {t("criticalBanner", { count: critical })}
          </span>
          <Link href={localePath(locale, "/alertes")} className="btn-secondary min-h-touch">
            {t("seeAlerts")}
          </Link>
        </div>
      ) : null}
      <QueryState
        isPending={maps.isPending || devices.isPending}
        error={maps.error ?? devices.error}
        isEmpty={rows.length === 0}
        emptyLabel={t("empty")}
        onRetry={() => {
          maps.refetch();
          void devices.refetch();
        }}
      >
        <h2 className="glass m-0 w-fit !rounded-full px-4 py-1.5 text-lg font-bold text-ink">
          {t("fieldsHeading")}
        </h2>
        <ul className="stagger m-0 grid list-none gap-4 p-0 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((row) => (
            <FieldLiveCard key={row.fieldId} row={row} />
          ))}
        </ul>
        <section aria-labelledby="dashboard-sources" className="card flex flex-col gap-2">
          <h2 id="dashboard-sources" className="text-base font-semibold">
            {t("sources")}
          </h2>
          {maps.maps.map((m) => (
            <div key={m.farmId} className="flex flex-col gap-1">
              <p className="text-sm text-mute">{t("sourceFarm", { farm: m.farmName })}</p>
              <ProvenanceNote provenance={m.map.provenance} />
            </div>
          ))}
        </section>
      </QueryState>
    </section>
  );
}

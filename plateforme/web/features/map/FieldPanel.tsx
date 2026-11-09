"use client";

import { useLocale, useTranslations } from "next-intl";
import Link from "next/link";

import { ProvenanceNote } from "@/components/Provenance";
import { QueryState } from "@/components/QueryState";
import { RampSwatch } from "@/components/RampSwatch";
import { useWeather } from "@/services/ai/weather";
import type { Locale } from "@/i18n/routing";
import { ApiError } from "@/lib/api";
import { MISSING, formatNumber, formatPct, formatWeekday } from "@/lib/format";
import type { MapFieldShape } from "@/lib/map-style";
import { localePath } from "@/lib/nav";

/** Jours de prévision montrés dans le panneau ; la vue Météo garde les 7 jours (même requête, même cache). */
const PANEL_DAYS = 3;

function FieldWeather({ fieldId }: { fieldId: string }) {
  const t = useTranslations("map.panel");
  const weather = useWeather(fieldId);
  if (weather.error instanceof ApiError && weather.error.code === "LOCATION_REQUIRED") {
    return <p className="text-sm text-warn-ink">{t("locationRequired")}</p>;
  }
  const days = weather.data?.days.slice(0, PANEL_DAYS) ?? [];
  return (
    <QueryState
      isPending={weather.isPending}
      error={weather.error}
      isEmpty={days.length === 0}
      emptyLabel={t("weatherEmpty")}
      onRetry={() => void weather.refetch()}
    >
      <ul className="flex flex-col gap-1 text-sm">
        {days.map((d) => (
          <li key={d.date} className="flex flex-wrap justify-between gap-2">
            <span className="font-semibold">{formatWeekday(d.date)}</span>
            <span>
              {t("temp", { max: formatNumber(d.t_max_c), min: formatNumber(d.t_min_c) })} ·{" "}
              {t("rain", { value: formatNumber(d.precipitation_mm, 1) })}
            </span>
          </li>
        ))}
      </ul>
      {weather.data ? <ProvenanceNote provenance={weather.data.provenance} /> : null}
    </QueryState>
  );
}

/** Panneau de la parcelle choisie sur la carte : valeurs de la carte, météo à 3 jours, liens vers le détail. */
export function FieldPanel({ field, farmName }: { field: MapFieldShape; farmName: string }) {
  const t = useTranslations("map");
  const locale = useLocale() as Locale;
  const p = field.props;
  const query = `?parcelle=${encodeURIComponent(p.field_id)}`;

  return (
    <section aria-labelledby="map-panel-title" className="card flex flex-col gap-3">
      <header>
        <h2 id="map-panel-title" className="text-lg font-semibold">
          {p.name}
        </h2>
        <p className="text-sm text-mute">{farmName}</p>
      </header>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-mute">{t("panel.crop")}</dt>
        <dd>{p.crop ?? t("panel.bareSoil")}</dd>
        {p.crop_type ? (
          <>
            <dt className="text-mute">{t("panel.detected")}</dt>
            <dd>{p.crop_type.probability === null ? t("panel.uncertain") : p.crop_type.label}</dd>
          </>
        ) : null}
        <dt className="text-mute">{t("panel.moisture")}</dt>
        <dd className="flex items-center gap-2">
          <RampSwatch moisture={p.soil_moisture_pct} size="sm" />
          {formatPct(p.soil_moisture_pct)}
        </dd>
        <dt className="text-mute">{t("panel.ndvi")}</dt>
        <dd>{p.ndvi === null ? MISSING : formatNumber(p.ndvi, 2)}</dd>
        {p.salinity_class ? (
          <>
            <dt className="text-mute">{t("panel.salinity")}</dt>
            <dd>{t(`canvas.salinityClass.${p.salinity_class}`)}</dd>
          </>
        ) : null}
        <dt className="text-mute">{t("panel.area")}</dt>
        <dd>{p.area_ha === null ? MISSING : t("panel.areaValue", { value: formatNumber(p.area_ha, 2) })}</dd>
        <dt className="text-mute">{t("panel.alerts")}</dt>
        <dd>{formatNumber(p.open_alerts)}</dd>
      </dl>
      <h3 className="font-semibold">{t("panel.weatherTitle", { days: PANEL_DAYS })}</h3>
      <FieldWeather fieldId={p.field_id} />
      <nav aria-label={t("panel.links")} className="flex flex-wrap gap-2">
        <Link
          href={localePath(locale, `/parcelles/${encodeURIComponent(p.field_id)}`)}
          className="btn-secondary"
        >
          {t("panel.detail")}
        </Link>
        <Link href={`${localePath(locale, "/recommandations")}${query}`} className="btn-secondary">
          {t("panel.recommendations")}
        </Link>
        <Link href={`${localePath(locale, "/meteo")}${query}`} className="btn-secondary">
          {t("panel.weather")}
        </Link>
      </nav>
    </section>
  );
}

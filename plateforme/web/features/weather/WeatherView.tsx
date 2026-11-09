"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { Chart } from "@/components/chart/Chart";
import { FieldPicker } from "@/components/FieldPicker";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { ProvenanceNote } from "@/components/Provenance";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { TimeAgo } from "@/components/TimeAgo";
import { WeatherHero } from "@/components/WeatherHero";
import { FORECAST_DAYS, useWeather } from "@/services/ai/weather";
import { useAllFields } from "@/hooks/places";
import { ApiError } from "@/lib/api";
import type { ChartSpec, ValueFormatter } from "@/lib/chart-option";
import type { WeatherForecastView } from "@/lib/contracts/field";
import { formatNumber, formatWeekday } from "@/lib/format";
import type { Tone } from "@/lib/status";
import type { WeatherDay, WeatherForecast } from "@/lib/types";

const formatTemp: ValueFormatter = (v) => (v === null ? formatNumber(v) : `${formatNumber(v, 1)} °C`);
const formatMm: ValueFormatter = (v) => (v === null ? formatNumber(v) : `${formatNumber(v, 1)} mm`);

const SOURCE_TONE: Record<WeatherForecast["source"], Tone> = {
  provider: "ok",
  cache: "info",
  stale_cache: "warn",
};

function sum(days: readonly WeatherDay[], pick: (d: WeatherDay) => number | null): number | null {
  const values = days.map(pick).filter((v): v is number => v !== null);
  return values.length === 0 ? null : values.reduce((a, b) => a + b, 0);
}

function extreme(days: readonly WeatherDay[], pick: (d: WeatherDay) => number | null, op: "max" | "min") {
  const values = days.map(pick).filter((v): v is number => v !== null);
  return values.length === 0 ? null : Math[op](...values);
}

function WeatherKpis({ days }: { days: readonly WeatherDay[] }) {
  const t = useTranslations("weather");
  const show = (v: number | null) => (v === null ? formatNumber(v) : formatNumber(v, 1));
  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <KpiCard
        label={t("kpiTMax")}
        value={show(extreme(days, (d) => d.t_max_c, "max"))}
        unit="°C"
        icon="thermometer"
      />
      <KpiCard
        label={t("kpiTMin")}
        value={show(extreme(days, (d) => d.t_min_c, "min"))}
        unit="°C"
        icon="thermometer"
      />
      <KpiCard
        label={t("kpiRain")}
        value={show(sum(days, (d) => d.precipitation_mm))}
        unit="mm"
        icon="rain"
      />
      <KpiCard label={t("kpiEt0")} value={show(sum(days, (d) => d.et0_mm))} unit="mm" icon="sun" />
    </dl>
  );
}

function useWeatherSpecs(forecast: WeatherForecast | undefined) {
  const t = useTranslations("weather");
  return useMemo(() => {
    if (!forecast || forecast.days.length === 0) return null;
    const days = forecast.days;
    const categories = days.map((d) => formatWeekday(d.date));
    const temp: ChartSpec = {
      categories,
      series: [
        { id: "tmax", name: t("tMax"), kind: "line", values: days.map((d) => d.t_max_c) },
        { id: "tmin", name: t("tMin"), kind: "line", values: days.map((d) => d.t_min_c) },
      ],
      unit: "°C",
      summary: t("tempSummary", { days: days.length }),
    };
    const rain: ChartSpec = {
      categories,
      series: [{ id: "rain", name: t("rain"), kind: "bar", values: days.map((d) => d.precipitation_mm) }],
      unit: "mm",
      yMin: 0,
      summary: t("rainSummary", { days: days.length, total: formatMm(sum(days, (d) => d.precipitation_mm)) }),
    };
    const et0: ChartSpec = {
      categories,
      series: [{ id: "et0", name: t("et0"), kind: "bar", values: days.map((d) => d.et0_mm) }],
      unit: "mm",
      yMin: 0,
      summary: t("et0Summary", { days: days.length, total: formatMm(sum(days, (d) => d.et0_mm)) }),
    };
    return { temp, rain, et0 };
  }, [forecast, t]);
}

function ForecastSource({ forecast }: { forecast: WeatherForecastView }) {
  const t = useTranslations("weather");
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <StatusTag tone={SOURCE_TONE[forecast.source]} label={t(`source.${forecast.source}`)} />
      <span className="text-mute">
        {t("provider", { provider: forecast.provider })} · <TimeAgo value={forecast.fetched_at} />
      </span>
      <div className="basis-full">
        <ProvenanceNote provenance={forecast.provenance} />
      </div>
    </div>
  );
}

/** Météo (module 5) : prévisions à 7 jours de la parcelle choisie, un graphique par grandeur. */
export function WeatherView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("weather");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const weather = useWeather(fieldId);
  const specs = useWeatherSpecs(weather.data);
  const needsLocation = weather.error instanceof ApiError && weather.error.code === "LOCATION_REQUIRED";

  return (
    <ModuleShell title={tm("weather")} description={t("description")}>
      <QueryState
        isPending={all.isPending}
        error={all.error}
        isEmpty={all.fields.length === 0}
        emptyLabel={t("noFields")}
        onRetry={all.refetch}
      >
        <FieldPicker farms={all.farms} fields={all.fields} value={fieldId} onChange={setFieldId} />
        {needsLocation ? (
          <p className="card text-warn-ink">{t("locationRequired")}</p>
        ) : (
          <QueryState
            isPending={weather.isPending}
            error={weather.error}
            isEmpty={specs === null}
            emptyLabel={t("empty")}
            onRetry={() => void weather.refetch()}
          >
            {weather.data && specs ? (
              <div className="flex flex-col gap-4">
                <ForecastSource forecast={weather.data} />
                {weather.data.source === "stale_cache" ? (
                  <p className="text-sm text-warn-ink">{t("staleNote")}</p>
                ) : null}
                <WeatherHero days={weather.data.days} />
                <WeatherKpis days={weather.data.days} />
                <Chart
                  title={t("tempTitle", { days: FORECAST_DAYS })}
                  spec={specs.temp}
                  formatValue={formatTemp}
                />
                <Chart
                  title={t("rainTitle", { days: FORECAST_DAYS })}
                  spec={specs.rain}
                  formatValue={formatMm}
                />
                <Chart
                  title={t("et0Title", { days: FORECAST_DAYS })}
                  spec={specs.et0}
                  formatValue={formatMm}
                />
              </div>
            ) : null}
          </QueryState>
        )}
      </QueryState>
    </ModuleShell>
  );
}

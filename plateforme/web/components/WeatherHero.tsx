"use client";

import { useTranslations } from "next-intl";

import { formatNumber, formatWeekday } from "@/lib/format";
import type { WeatherDay } from "@/lib/types";

import { Icon, type IconName } from "./Icon";
import { Furrows, SkyArt, type SkyKind } from "./Illustrations";

const RAIN_LIGHT_MM = 1;
const RAIN_HEAVY_MM = 5;
const DAYS_SHOWN = 7;

/** Situation du ciel déduite de la seule pluie prévue : aucune couverture nuageuse n'est inventée. */
export function skyKind(precipitationMm: number | null): SkyKind {
  const mm = precipitationMm ?? 0;
  if (mm >= RAIN_HEAVY_MM) return "rain";
  if (mm >= RAIN_LIGHT_MM) return "light";
  return "dry";
}

export const SKY_CLASS: Record<SkyKind, string> = { dry: "sky-dry", light: "sky-light", rain: "sky-rain" };
const SKY_ICON: Record<SkyKind, IconName> = { dry: "sun", light: "cloudsun", rain: "rain" };

/**
 * Météo immersive : un ciel illustré et animé (soleil, nuage, pluie) derrière la température du jour,
 * puis la semaine en tuiles de verre. Toutes les valeurs viennent de la prévision ; seule la pluie choisit le décor.
 */
export function WeatherHero({ days, title }: { days: readonly WeatherDay[]; title?: string }) {
  const t = useTranslations("weather.hero");
  const today = days[0];
  if (!today) return null;
  const kind = skyKind(today.precipitation_mm);
  const week = days.slice(0, DAYS_SHOWN);
  return (
    <section className={`sky reveal ${SKY_CLASS[kind]}`} aria-label={title ?? t("today")}>
      <Furrows className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-28 w-full text-white" />
      <div className="grid items-center gap-4 p-5 sm:p-8 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <p className="m-0 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-white">
            <Icon name={SKY_ICON[kind]} size={18} />
            {title ?? t("today")}
          </p>
          <p className="m-0 text-6xl font-bold tracking-tight tabular-nums text-white sm:text-7xl">
            {t("range", { max: formatNumber(today.t_max_c, 0), min: formatNumber(today.t_min_c, 0) })}
          </p>
          <p className="m-0 text-xl font-semibold text-white">{t(kind)}</p>
          <ul className="m-0 flex list-none flex-wrap gap-2 p-0">
            <li className="sky-tile !flex-row !gap-2 !px-3 !py-1.5 text-sm font-semibold text-white">
              <Icon name="rain" size={16} />
              {t("rainMm", { mm: formatNumber(today.precipitation_mm, 1) })}
            </li>
            <li className="sky-tile !flex-row !gap-2 !px-3 !py-1.5 text-sm font-semibold text-white">
              <Icon name="drops" size={16} />
              {t("et0Mm", { mm: formatNumber(today.et0_mm, 1) })}
            </li>
          </ul>
        </div>
        <div className="flex justify-center md:justify-end">
          <SkyArt kind={kind} size={190} />
        </div>
      </div>
      <div className="px-5 pb-5 sm:px-8 sm:pb-8">
        <h2 className="mb-2 mt-0 text-sm font-semibold text-white">{t("week")}</h2>
        <ul className="stagger m-0 grid list-none grid-cols-4 gap-2 p-0 sm:grid-cols-7">
          {week.map((day) => (
            <li key={day.date} className="sky-tile text-white">
              <span className="text-xs font-semibold">{formatWeekday(day.date)}</span>
              <Icon name={SKY_ICON[skyKind(day.precipitation_mm)]} size={22} />
              <span className="text-base font-bold tabular-nums">{formatNumber(day.t_max_c, 0)} °</span>
              <span className="text-xs tabular-nums text-white">{formatNumber(day.t_min_c, 0)} °</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

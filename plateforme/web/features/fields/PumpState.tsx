"use client";

import { useTranslations } from "next-intl";

import { StatusTag } from "@/components/StatusTag";
import type { Measurement } from "@/lib/types";

/** Durées imposées par le firmware v1.1 (affichage seulement : le kit reste seul juge). */
export const PUMP_MAX_RUN_MIN = 10;
export const PUMP_LOCK_MIN = 30;

/**
 * État de la pompe en lecture seule. La commande manuelle passe par l'application mobile, au bord du champ :
 * le serveur ne joint pas le kit (ADR 007).
 */
export function PumpState({ measurement }: { measurement: Measurement | null }) {
  const t = useTranslations("pump");
  const on = measurement?.pump_on ?? null;
  const fault = measurement?.pump_fault === true;

  return (
    <section className="card flex flex-col gap-3" aria-labelledby="pump-title">
      <h2 id="pump-title" className="text-lg font-semibold">
        {t("title")}
      </h2>
      <div className="flex flex-wrap gap-2">
        {on === null ? (
          <StatusTag tone="info" label={t("unknown")} />
        ) : (
          <StatusTag tone={on ? "ok" : "info"} label={on ? t("on") : t("off")} />
        )}
        {fault ? <StatusTag tone="bad" label={t("fault")} /> : null}
      </div>
      {fault ? <p className="text-sm font-semibold text-bad-ink">{t("faultHelp")}</p> : null}
      <p className="text-sm">{t("rules", { maxRun: PUMP_MAX_RUN_MIN, lock: PUMP_LOCK_MIN })}</p>
      <p className="text-sm text-mute">{t("mobileOnly")}</p>
    </section>
  );
}

"use client";

import { useTranslations } from "next-intl";

import { ProvenanceNote } from "@/components/Provenance";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import type { DeviceHealth } from "@/lib/contracts/device";
import { pumpRiskView, sensorTone, worstState } from "@/lib/device-health";
import { formatDateTime, formatPct } from "@/lib/format";
import { useDeviceHealth } from "@/services/ai/device-health";

function PumpRisk({ health }: { health: DeviceHealth }) {
  const t = useTranslations("kitHealth");
  const view = pumpRiskView(health.pump_failure_48h, health.provenance.confidence.calibrated);
  const text =
    view.type === "percent"
      ? formatPct(view.value)
      : view.type === "uncalibrated"
        ? t("riskUncalibrated")
        : "—";
  return (
    <p>
      <span className="text-mute">{t("pumpRisk")} : </span>
      <span className="font-semibold">{text}</span>
    </p>
  );
}

function HealthCards({ health }: { health: DeviceHealth }) {
  const t = useTranslations("kitHealth");
  const worst = worstState(health.sensors);
  return (
    <div className="flex flex-col gap-3">
      {worst ? (
        <div role="status">
          <StatusTag tone={sensorTone(worst)} label={t(`overall.${worst}`)} />
        </div>
      ) : null}
      <ul className="flex flex-col gap-2">
        {health.sensors.map((s) => (
          <li key={s.sensor} className="card flex flex-wrap items-center justify-between gap-2">
            <span className="font-semibold">{t(`sensors.${s.sensor}`)}</span>
            <span className="flex flex-col items-end gap-1">
              <StatusTag tone={sensorTone(s.state)} label={t(`states.${s.state}`)} />
              {s.since ? (
                <span className="text-xs text-mute">{t("since", { date: formatDateTime(s.since) })}</span>
              ) : null}
            </span>
          </li>
        ))}
      </ul>
      <PumpRisk health={health} />
      <p className="text-xs text-mute">{t("checkedAt", { date: formatDateTime(health.checked_at) })}</p>
      <ProvenanceNote provenance={health.provenance} />
    </div>
  );
}

/** Santé du kit (service 13, doc 18 §10) : état par capteur et risque de panne de pompe à 48 h. */
export function KitHealth({ deviceId }: { deviceId: string }) {
  const t = useTranslations("kitHealth");
  const query = useDeviceHealth(deviceId);
  return (
    <section className="flex flex-col gap-2" aria-label={t("title")}>
      <h2 className="font-semibold">{t("title")}</h2>
      <QueryState
        isPending={query.isPending}
        error={query.error}
        isEmpty={!query.data || query.data.sensors.length === 0}
        emptyLabel={t("empty")}
        onRetry={() => void query.refetch()}
      >
        {query.data ? <HealthCards health={query.data} /> : null}
      </QueryState>
    </section>
  );
}

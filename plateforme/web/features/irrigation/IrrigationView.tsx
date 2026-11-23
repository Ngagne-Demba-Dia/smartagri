"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { AiCard } from "@/components/AiCard";
import { FieldPicker } from "@/components/FieldPicker";
import { Icon } from "@/components/Icon";
import { KpiCard } from "@/components/KpiCard";
import { Meter } from "@/components/Meter";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { useAllFields } from "@/hooks/places";
import type { IrrigationNeed } from "@/lib/contracts/field";
import { formatNumber } from "@/lib/format";
import {
  climaticDemand,
  isDegraded,
  readingKind,
  waterQualityForField,
  type WaterCloggingRisk,
  type WaterPhState,
} from "@/lib/irrigation";
import type { Tone } from "@/lib/status";
import { useIrrigationNeed } from "@/services/ai/irrigation-need";
import { useWeather } from "@/services/ai/weather";

const WEEK_DAYS = 7;
const PH_TONE: Record<WaterPhState, Tone> = { optimal: "ok", acidic: "info", alkaline: "warn" };
const CLOG_TONE: Record<WaterCloggingRisk, Tone> = { low: "ok", medium: "warn", high: "bad" };

function Reading({ need }: { need: IrrigationNeed }) {
  const t = useTranslations("irrigation");
  const kind = readingKind(need);
  const text = t(`reading.${kind}`, { mm: formatNumber(need.need_mm, 1), reason: need.defer_reason ?? "" });
  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-semibold">{t("readingTitle")}</h3>
      <p className="m-0">{text}</p>
      {isDegraded(need) ? <p className="m-0 text-sm text-warn-ink">{t("readingDegraded")}</p> : null}
      <p className="m-0 text-xs text-mute">{t("unitEquivalence")}</p>
      <p className="m-0 text-xs text-mute">{t("readingNote")}</p>
    </div>
  );
}

function NeedCards({ need }: { need: IrrigationNeed }) {
  const t = useTranslations("irrigation");
  const rain =
    need.rain_expected_mm === null
      ? t("deferRainUnknown")
      : t("deferRain", { mm: formatNumber(need.rain_expected_mm, 1) });
  return (
    <AiCard title={t("needTitle")} provenance={need.provenance} unit=" mm">
      <div className="flex flex-col gap-4">
        <dl className="grid gap-3 sm:grid-cols-2">
          <KpiCard
            label={t("todayTitle")}
            value={t("todayValue", { mm: formatNumber(need.need_mm, 1) })}
            icon="drop"
          />
          <KpiCard
            label={t("volumeLabel")}
            value={
              need.volume_m3 === null
                ? t("volumeNone")
                : t("volumeValue", { m3: formatNumber(need.volume_m3, 1) })
            }
            icon="drops"
          />
        </dl>
        {need.defer ? (
          <div role="status" className="flex flex-col gap-1 rounded-card bg-warn-bg p-3 text-warn-ink">
            <StatusTag tone="warn" label={t("deferTitle")} />
            {need.defer_reason ? <p className="m-0">{need.defer_reason}</p> : null}
            <p className="m-0 text-sm">{rain}</p>
          </div>
        ) : null}
        <Reading need={need} />
      </div>
    </AiCard>
  );
}

/** Demande climatique à 7 jours : dérivée du service météo, indépendante du service 3 (doc 18 §3). */
function WeekDemand({ fieldId }: { fieldId: string }) {
  const t = useTranslations("irrigation");
  const weather = useWeather(fieldId, WEEK_DAYS);
  const demand = weather.data ? climaticDemand(weather.data.days) : null;
  return (
    <AiCard title={t("weekTitle")} provenance={weather.data?.provenance ?? null} unit=" mm">
      {weather.isPending ? (
        <p className="m-0 text-mute">…</p>
      ) : weather.error ? (
        <p className="m-0 text-warn-ink">{t("weekError")}</p>
      ) : demand ? (
        <div className="flex flex-col gap-2">
          <p className="m-0 text-2xl font-bold">{t("weekValue", { mm: formatNumber(demand.demandMm, 1) })}</p>
          <p className="m-0 text-sm">
            {t("weekDetail", {
              et: formatNumber(demand.etMm, 1),
              rain: formatNumber(demand.rainMm, 1),
              days: demand.daysCounted,
            })}
          </p>
        </div>
      ) : (
        <p className="m-0">{t("weekEmpty")}</p>
      )}
      <p className="m-0 mt-2 text-xs text-mute">{t("weekNote")}</p>
    </AiCard>
  );
}

/** Capteur pH & Nature de l'eau d'irrigation : pH, nature chimique, salinité CE, température et risque de colmatage. */
function WaterQualityCard({ fieldId }: { fieldId: string }) {
  const t = useTranslations("irrigation");
  const wq = waterQualityForField(fieldId);
  return (
    <section aria-label={t("waterQuality.title")} className="card flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="m-0 flex items-center gap-2 text-lg font-bold text-ink">
          <Icon name="kit" size={20} />
          {t("waterQuality.title")}
        </h2>
        <StatusTag tone={PH_TONE[wq.phState]} label={t(`waterQuality.state.${wq.phState}`)} />
      </div>

      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label={t("waterQuality.kpiPh")}
          value={`${formatNumber(wq.ph, 1)} pH`}
          hint={t("waterQuality.optimalRange")}
          icon="kit"
        />
        <KpiCard
          label={t("waterQuality.kpiNature")}
          value={t(`waterQuality.nature.${wq.phState}`)}
          hint={t(`waterQuality.source.${wq.sourceKind}`)}
          icon="drop"
        />
        <KpiCard
          label={t("waterQuality.kpiEc")}
          value={`${formatNumber(wq.ecDsM, 1)} dS/m`}
          hint={t("waterQuality.tempValue", { temp: formatNumber(wq.waterTempC, 1) })}
          icon="activity"
        />
        <KpiCard
          label={t("waterQuality.kpiClogging")}
          value={t(`waterQuality.clogging.${wq.cloggingRisk}`)}
          icon="pump"
        >
          <StatusTag tone={CLOG_TONE[wq.cloggingRisk]} label={t(`waterQuality.clogging.${wq.cloggingRisk}`)} />
        </KpiCard>
      </dl>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="font-semibold">{t("waterQuality.scaleLabel")}</span>
          <span className="tabular-nums text-mute">
            pH {formatNumber(wq.ph, 1)} ({t("waterQuality.optimalRange")})
          </span>
        </div>
        <Meter
          value={wq.meterPct}
          label={t("waterQuality.scaleLabel")}
          valueText={`pH ${formatNumber(wq.ph, 1)}`}
          marks={[
            { value: 40, label: t("waterQuality.markMin") },
            { value: 64, label: t("waterQuality.markMax") },
          ]}
        />
      </div>

      <div className="rounded-btn bg-surface p-3 text-sm">
        <p className="m-0 font-semibold text-ink">{t(`waterQuality.diagnosis.${wq.phState}`)}</p>
        <p className="m-0 mt-1 text-mute">{t(`waterQuality.advice.${wq.phState}`)}</p>
      </div>
    </section>
  );
}

/** Irrigation (service 3, doc 18 §3) : besoin à 24 h, capteur pH & nature de l'eau, demande climatique à 7 jours. */
export function IrrigationView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("irrigation");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const need = useIrrigationNeed(fieldId);

  return (
    <ModuleShell title={tm("irrigation")} description={t("description")}>
      <QueryState
        isPending={all.isPending}
        error={all.error}
        isEmpty={all.fields.length === 0}
        emptyLabel={t("noFields")}
        onRetry={all.refetch}
      >
        <FieldPicker farms={all.farms} fields={all.fields} value={fieldId} onChange={setFieldId} />
        {fieldId ? (
          <div className="flex flex-col gap-4">
            <QueryState
              isPending={need.isPending}
              error={need.error}
              isEmpty={!need.data}
              emptyLabel={t("empty")}
              onRetry={() => void need.refetch()}
            >
              {need.data ? <NeedCards need={need.data} /> : null}
            </QueryState>
            <WaterQualityCard fieldId={fieldId} />
            <WeekDemand fieldId={fieldId} />
          </div>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

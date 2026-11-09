"use client";

import { useTranslations } from "next-intl";

import {
  confidenceView,
  provenanceState,
  type Confidence,
  type Provenance,
  type ProvenanceState,
} from "@/lib/contracts/provenance";
import { formatNumber, formatPct } from "@/lib/format";
import type { Tone } from "@/lib/status";

import { StatusTag } from "./StatusTag";
import { TimeAgo } from "./TimeAgo";

const STATE_TONE: Record<ProvenanceState, Tone> = { fresh: "ok", stale: "warn", fallback: "warn" };
const PERCENT = 100;

/** Confiance telle que l'écran a le droit de la montrer (doc 16 §6.3) : jamais un % non calibré. */
export function ConfidenceText({ confidence, unit = "" }: { confidence: Confidence; unit?: string }) {
  const tc = useTranslations("provenance.confidence");
  const view = confidenceView(confidence);
  if (view.type === "percent") return <>{tc("percent", { value: formatPct(view.value * PERCENT) })}</>;
  if (view.type === "uncalibrated") return <>{tc("uncalibrated")}</>;
  if (view.type === "none") return <>{tc("none")}</>;
  const bounds = { p10: `${formatNumber(view.p10, 1)}${unit}`, p90: `${formatNumber(view.p90, 1)}${unit}` };
  return <>{view.calibrated ? tc("interval", bounds) : tc("intervalUncalibrated", bounds)}</>;
}

/**
 * Bloc de provenance de doc 16 §9.2 : état (à jour, périmé, secours), modèle et version, source,
 * âge du calcul et des données, confiance. Sans bloc (route existante non encore enrichie) :
 * « provenance non communiquée », jamais une provenance supposée.
 */
export function ProvenanceNote({ provenance, unit }: { provenance: Provenance | null; unit?: string }) {
  const t = useTranslations("provenance");
  if (!provenance) return <p className="text-xs text-mute">{t("missing")}</p>;
  const state = provenanceState(provenance);
  return (
    <div
      role="group"
      aria-label={t("title")}
      className="flex flex-col gap-2 rounded-btn border border-glass-edge bg-surface p-3 text-sm shadow-[inset_0_1px_0_var(--glass-rim)]"
    >
      <div className="flex flex-wrap items-center gap-2">
        <StatusTag tone={STATE_TONE[state]} label={t(`state.${state}`)} />
        <span className="font-semibold">
          {t("model", { name: provenance.model_name, version: provenance.model_version })}
        </span>
        <span className="chip">{t(`source.${provenance.source}`)}</span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
        <dt className="text-mute">{t("computedAt")}</dt>
        <dd>
          <TimeAgo value={provenance.computed_at} />
        </dd>
        {provenance.data_as_of ? (
          <>
            <dt className="text-mute">{t("dataAsOf")}</dt>
            <dd>
              <TimeAgo value={provenance.data_as_of} />
            </dd>
          </>
        ) : null}
        <dt className="text-mute">{t("confidenceLabel")}</dt>
        <dd>
          <ConfidenceText confidence={provenance.confidence} unit={unit} />
        </dd>
        {provenance.fallback_step > 0 ? (
          <>
            <dt className="text-mute">{t("fallbackLabel")}</dt>
            <dd>{t(`fallback.step${provenance.fallback_step}`)}</dd>
          </>
        ) : null}
      </dl>
    </div>
  );
}

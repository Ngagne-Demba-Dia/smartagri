"use client";

import { useTranslations } from "next-intl";

import { DataTable, type Column } from "@/components/DataTable";
import { Icon, type IconName } from "@/components/Icon";
import { AdvisorAvatar } from "@/components/Illustrations";
import { ProvenanceNote } from "@/components/Provenance";
import { useErrorMessage } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { TimeAgo } from "@/components/TimeAgo";
import { useRecommendationFeedback } from "@/services/ai/recommendations";
import type { RecommendationView } from "@/lib/contracts/field";
import { MISSING, formatNumber } from "@/lib/format";
import type { Tone } from "@/lib/status";
import type {
  FertilizationPayload,
  IrrigationAction,
  IrrigationPayload,
  NutrientStatus,
  RecommendationFeedback,
} from "@/lib/types";

export const ACTION_TONE: Record<IrrigationAction, Tone> = {
  irriguer: "warn",
  ne_pas_irriguer: "ok",
  surveiller: "info",
  verifier_capteur: "bad",
};

const ACTION_ICON: Record<IrrigationAction, IconName> = {
  irriguer: "drops",
  ne_pas_irriguer: "check",
  surveiller: "target",
  verifier_capteur: "wrench",
};

const DECISION_CLASS: Record<Tone, string> = {
  ok: "bg-ok-bg text-ok-ink",
  warn: "bg-warn-bg text-warn-ink",
  bad: "bg-bad-bg text-bad-ink",
  info: "bg-card text-ink",
};

/** Un jalon de la démarche du conseiller (constat, dose, à savoir) sur le fil vertical. */
function Step({ title, icon, children }: { title: string; icon: IconName; children: React.ReactNode }) {
  return (
    <div className="relative flex flex-col gap-2">
      <span
        className="absolute -left-7 top-0 inline-flex h-4 w-4 items-center justify-center rounded-full border-2 border-white bg-accent text-white shadow"
        aria-hidden="true"
      />
      <h3 className="m-0 flex items-center gap-1.5 text-sm font-bold uppercase tracking-wide text-g">
        <Icon name={icon} size={16} />
        {title}
      </h3>
      {children}
    </div>
  );
}

const LEVEL_TONE: Record<NonNullable<NutrientStatus["level"]>, Tone> = {
  bas: "bad",
  moyen: "ok",
  eleve: "warn",
};

const FEEDBACK_VALUES: readonly RecommendationFeedback[] = [
  "followed",
  "partially_followed",
  "ignored",
  "not_applicable",
];

const mm = (v: number | null) => (v === null ? MISSING : `${formatNumber(v, 1)} mm`);

function IrrigationBody({ payload }: { payload: IrrigationPayload }) {
  const t = useTranslations("recommendations");
  const ta = useTranslations("recommendations.advisor");
  const { advice } = payload;
  const tone = ACTION_TONE[advice.action];
  return (
    <>
      <div className={`decision pop ${DECISION_CLASS[tone]}`}>
        <span className="decision-icon" aria-hidden="true">
          <Icon name={ACTION_ICON[advice.action]} size={24} />
        </span>
        <span className="flex flex-col">
          <span className="text-xs font-semibold uppercase tracking-wide">{ta("decision")}</span>
          <span className="text-xl font-bold leading-tight sm:text-2xl">{t(`actions.${advice.action}`)}</span>
        </span>
      </div>
      <div className="advisor-bubble flex items-start gap-2.5">
        <span className="mt-0.5 shrink-0 text-g" aria-hidden="true">
          <Icon name="chat" size={18} />
        </span>
        <p className="m-0 text-base font-medium text-ink sm:text-lg">{advice.reason}</p>
      </div>
      <div className="step-line">
        <Step title={ta("finding")} icon="activity">
          <dl className="m-0 grid grid-cols-2 gap-2 text-sm md:grid-cols-3">
            <div className="tile">
              <dt className="text-mute">{t("thresholds")}</dt>
              <dd className="m-0 font-semibold tabular-nums">
                {t("thresholdsValue", { start: payload.thresholds.start_pct, stop: payload.thresholds.stop_pct })}
              </dd>
            </div>
            <div className="tile">
              <dt className="text-mute">{t("et0")}</dt>
              <dd className="m-0 text-base font-bold tabular-nums">{mm(payload.et0_mm)}</dd>
            </div>
            <div className="tile">
              <dt className="text-mute">{t("measuredAt")}</dt>
              <dd className="m-0 font-semibold">
                <TimeAgo value={payload.measured_at} />
              </dd>
            </div>
          </dl>
        </Step>
        <Step title={ta("dose")} icon="drops">
          <dl className="m-0 grid grid-cols-3 gap-2 text-sm">
            <div className="tile items-center text-center">
              <dt className="text-mute">{t("netMm")}</dt>
              <dd className="m-0 text-xl font-bold tabular-nums text-g">{mm(advice.net_mm)}</dd>
            </div>
            <div className="tile items-center text-center">
              <dt className="text-mute">{t("grossMm")}</dt>
              <dd className="m-0 text-xl font-bold tabular-nums text-g">{mm(advice.gross_mm)}</dd>
            </div>
            <div className="tile items-center text-center">
              <dt className="text-mute">{t("volume")}</dt>
              <dd className="m-0 text-xl font-bold tabular-nums text-g">
                {advice.volume_m3 === null ? MISSING : `${formatNumber(advice.volume_m3, 1)} m³`}
              </dd>
            </div>
          </dl>
        </Step>
        <Step title={ta("caution")} icon="info">
          <p className="m-0 text-sm text-mute">{advice.caveat}</p>
        </Step>
      </div>
    </>
  );
}

function FertilizationBody({ payload }: { payload: FertilizationPayload }) {
  const t = useTranslations("recommendations");
  const columns: ReadonlyArray<Column<NutrientStatus>> = [
    { key: "nutrient", header: t("columns.nutrient"), cell: (n) => n.nutrient },
    {
      key: "value",
      header: t("columns.value"),
      cell: (n) => (n.value === null ? MISSING : `${formatNumber(n.value)} mg/kg`),
      numeric: true,
    },
    {
      key: "level",
      header: t("columns.level"),
      cell: (n) =>
        n.level ? <StatusTag tone={LEVEL_TONE[n.level]} label={t(`levels.${n.level}`)} /> : MISSING,
    },
    { key: "message", header: t("columns.message"), cell: (n) => n.message },
  ];
  const ta = useTranslations("recommendations.advisor");
  return (
    <div className="step-line">
      {payload.sensor_ok ? null : <StatusTag tone="bad" label={t("npkFault")} />}
      <Step title={ta("soil")} icon="sprout">
        <DataTable
          caption={t("nutrientsCaption")}
          columns={columns}
          rows={payload.nutrients}
          rowKey={(n) => n.nutrient}
        />
      </Step>
      <Step title={ta("caution")} icon="info">
        <p className="m-0 text-sm text-mute">{payload.caveat}</p>
      </Step>
    </div>
  );
}

function FeedbackButtons({
  recommendationId,
  sent,
  onSent,
}: {
  recommendationId: string;
  sent: RecommendationFeedback | undefined;
  onSent: (value: RecommendationFeedback) => void;
}) {
  const t = useTranslations("recommendations");
  const errorMessage = useErrorMessage();
  const mutation = useRecommendationFeedback();
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-semibold">{t("feedbackQuestion")}</p>
      <div role="group" aria-label={t("feedbackQuestion")} className="flex flex-wrap gap-2">
        {FEEDBACK_VALUES.map((value) => (
          <button
            key={value}
            type="button"
            className={sent === value ? "btn-primary" : "btn-secondary"}
            aria-pressed={sent === value}
            disabled={mutation.isPending}
            onClick={() =>
              mutation.mutate({ id: recommendationId, feedback: value }, { onSuccess: () => onSent(value) })
            }
          >
            {t(`feedback.${value}`)}
          </button>
        ))}
      </div>
      <p aria-live="polite" className="text-sm">
        {sent ? t("feedbackSaved") : ""}
      </p>
      {mutation.isError ? (
        <p role="alert" className="text-sm font-semibold text-bad-ink">
          {errorMessage(mutation.error)}
        </p>
      ) : null}
    </div>
  );
}

/** Une recommandation (irrigation ou fertilisation) avec, selon le rôle, le retour de l'exploitant. */
export function RecommendationCard({
  recommendation,
  canFeedback,
  sent,
  onSent,
}: {
  recommendation: RecommendationView;
  canFeedback: boolean;
  sent: RecommendationFeedback | undefined;
  onSent: (value: RecommendationFeedback) => void;
}) {
  const t = useTranslations("recommendations");
  const ta = useTranslations("recommendations.advisor");
  const cleanVersion = recommendation.engine_version.replace(/^[^@]+@/, "");
  return (
    <li className="card card-ai flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <span className="relative inline-flex shrink-0 drop-shadow-md" aria-hidden="true">
            <AdvisorAvatar size={56} />
            <span className="live-dot absolute bottom-0.5 right-0.5 ring-2 ring-white" />
          </span>
          <div className="flex flex-col">
            <p className="m-0 text-xs font-bold uppercase tracking-wide text-g">{ta("eyebrow")}</p>
            <h2 className="text-xl font-bold leading-tight">{t(`kind.${recommendation.kind}`)}</h2>
          </div>
        </div>
        <span className="chip">
          {t("engine", { version: cleanVersion })} ·{" "}
          <TimeAgo value={recommendation.created_at} />
        </span>
      </div>
      {recommendation.kind === "irrigation" ? (
        <IrrigationBody payload={recommendation.payload} />
      ) : (
        <FertilizationBody payload={recommendation.payload} />
      )}
      {recommendation.justification ? <p className="m-0 text-sm">{recommendation.justification}</p> : null}
      <p className="m-0 flex items-center gap-1.5 text-xs text-mute">
        <Icon name="shield" size={14} />
        {ta("disclaimer")}
      </p>
      <ProvenanceNote provenance={recommendation.provenance} />
      {canFeedback ? (
        <FeedbackButtons recommendationId={recommendation.id} sent={sent} onSent={onSent} />
      ) : null}
    </li>
  );
}

"use client";

import { useTranslations } from "next-intl";
import { useId, useState, type FormEvent } from "react";

import { useErrorMessage } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { TimeAgo } from "@/components/TimeAgo";
import { useUpdateThresholds } from "@/hooks/devices";
import { useMe } from "@/hooks/places";
import type { Tone } from "@/lib/status";
import { canEditThresholds } from "@/lib/roles";
import {
  THRESHOLD_MAX,
  THRESHOLD_MIN,
  THRESHOLD_MIN_GAP,
  validateThresholds,
  type ThresholdError,
} from "@/lib/thresholds";
import type { Device, SyncStatus } from "@/lib/types";

const SYNC_TONE: Record<SyncStatus, Tone> = { pending: "warn", sent: "info", applied: "ok", failed: "bad" };

function fieldErrors(errors: readonly ThresholdError[], field: "start" | "stop") {
  return errors.filter((e) => e.field === field);
}

/**
 * Seuils d'irrigation d'un kit. Même règle que le firmware v1.1 et l'API (lib/thresholds.ts).
 * La valeur enregistrée reste « en attente » jusqu'au passage du téléphone relais (ADR 007).
 */
export function ThresholdForm({ device }: { device: Device }) {
  const t = useTranslations("thresholds");
  const me = useMe();
  const errorMessage = useErrorMessage();
  const mutation = useUpdateThresholds(device.id);
  const startId = useId();
  const stopId = useId();
  const state = device.thresholds;
  const [start, setStart] = useState(String(state?.desired.start_pct ?? ""));
  const [stop, setStop] = useState(String(state?.desired.stop_pct ?? ""));
  const [errors, setErrors] = useState<ThresholdError[]>([]);
  const canEdit = canEditThresholds(me.data, device.organization_id);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = validateThresholds(start, stop);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors([]);
    mutation.mutate(result.value);
  };

  const renderErrors = (field: "start" | "stop", id: string) => {
    const list = fieldErrors(errors, field);
    if (list.length === 0) return null;
    return (
      <ul id={id} className="text-sm font-semibold text-bad-ink">
        {list.map((e) => (
          <li key={e.code}>{t(`errors.${e.code}`, { gap: THRESHOLD_MIN_GAP, max: THRESHOLD_MAX })}</li>
        ))}
      </ul>
    );
  };

  return (
    <section className="card flex flex-col gap-3" aria-labelledby="thresholds-title">
      <h2 id="thresholds-title" className="text-lg font-semibold">
        {t("title")}
      </h2>
      {state ? (
        <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
          <dt className="text-mute">{t("desired")}</dt>
          <dd className="tabular-nums">
            {t("pair", { start: state.desired.start_pct, stop: state.desired.stop_pct })}
          </dd>
          <dt className="text-mute">{t("reported")}</dt>
          <dd className="tabular-nums">
            {state.reported
              ? t("pair", { start: state.reported.start_pct, stop: state.reported.stop_pct })
              : t("notReported")}
          </dd>
          <dt className="text-mute">{t("syncLabel")}</dt>
          <dd>
            <StatusTag tone={SYNC_TONE[state.sync_status]} label={t(`sync.${state.sync_status}`)} />
          </dd>
          <dt className="text-mute">{t("updated")}</dt>
          <dd>
            <TimeAgo value={state.updated_at} />
          </dd>
        </dl>
      ) : (
        <p className="text-mute">{t("none")}</p>
      )}
      {state?.sync_status === "pending" ? (
        <p className="rounded-btn bg-warn-bg p-3 text-sm text-warn-ink">{t("relayNote")}</p>
      ) : null}

      {canEdit ? (
        <form onSubmit={submit} noValidate className="flex flex-col gap-3">
          <p className="text-sm text-mute">
            {t("rule", { min: THRESHOLD_MIN, gap: THRESHOLD_MIN_GAP, max: THRESHOLD_MAX })}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label htmlFor={startId} className="font-semibold">
                {t("start")}
              </label>
              <input
                id={startId}
                className="field-input tabular-nums"
                inputMode="numeric"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                aria-invalid={fieldErrors(errors, "start").length > 0}
                aria-describedby={fieldErrors(errors, "start").length > 0 ? `${startId}-err` : undefined}
              />
              {renderErrors("start", `${startId}-err`)}
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor={stopId} className="font-semibold">
                {t("stop")}
              </label>
              <input
                id={stopId}
                className="field-input tabular-nums"
                inputMode="numeric"
                value={stop}
                onChange={(e) => setStop(e.target.value)}
                aria-invalid={fieldErrors(errors, "stop").length > 0}
                aria-describedby={fieldErrors(errors, "stop").length > 0 ? `${stopId}-err` : undefined}
              />
              {renderErrors("stop", `${stopId}-err`)}
            </div>
          </div>
          <button type="submit" className="btn-primary self-start" disabled={mutation.isPending}>
            {mutation.isPending ? t("saving") : t("save")}
          </button>
          <p aria-live="polite" className="text-sm">
            {mutation.isSuccess ? t("saved") : ""}
          </p>
          {mutation.isError ? (
            <p role="alert" className="rounded-btn bg-bad-bg p-3 text-sm font-semibold text-bad-ink">
              {errorMessage(mutation.error)}
            </p>
          ) : null}
        </form>
      ) : (
        <p className="text-sm text-mute">{t("readOnly")}</p>
      )}
    </section>
  );
}

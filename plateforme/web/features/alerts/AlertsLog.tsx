"use client";

import { useTranslations } from "next-intl";
import { useId, useState } from "react";

import { Icon } from "@/components/Icon";
import { ModuleShell } from "@/components/ModuleShell";
import { ProvenanceNote } from "@/components/Provenance";
import { QueryState, useErrorMessage } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { TimeAgo } from "@/components/TimeAgo";
import { useAckAlert, useAlerts } from "@/services/ai/device-health";
import { useMe } from "@/hooks/places";
import { formatDateTime } from "@/lib/format";
import { canAckAlerts } from "@/lib/roles";
import { SEVERITY_TONE } from "@/lib/status";
import type { AlertView } from "@/lib/contracts/device";
import type { AlertStatus } from "@/lib/types";

type StatusFilter = AlertStatus | "all";
const FILTERS: readonly StatusFilter[] = ["open", "acknowledged", "resolved", "all"];

function AlertItem({ alert, canAck }: { alert: AlertView; canAck: boolean }) {
  const t = useTranslations("alerts");
  const errorMessage = useErrorMessage();
  const ack = useAckAlert();
  return (
    <li className="card flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <StatusTag tone={SEVERITY_TONE[alert.severity]} label={t(`severity.${alert.severity}`)} />
        <span className="text-sm text-mute">{t(`status.${alert.status}`)}</span>
        <span className="text-sm text-mute">
          <TimeAgo value={alert.created_at} />
        </span>
      </div>
      {/* Texte produit par le backend, rendu comme texte (jamais interprété en HTML). */}
      <p className="font-semibold">{alert.message}</p>
      <p className="text-sm text-mute">
        {t("rule", { rule: t.has(`rules.${alert.rule}`) ? t(`rules.${alert.rule}`) : alert.rule })} ·{" "}
        {formatDateTime(alert.created_at)}
      </p>
      {alert.acknowledged_at ? (
        <p className="text-sm text-mute">
          {t("acknowledgedAt", { date: formatDateTime(alert.acknowledged_at) })}
        </p>
      ) : null}
      <ProvenanceNote provenance={alert.provenance} />
      {canAck && alert.status === "open" ? (
        <button
          type="button"
          className="btn-secondary self-start"
          disabled={ack.isPending}
          onClick={() => ack.mutate(alert.id)}
        >
          {ack.isPending ? t("acking") : t("ack")}
        </button>
      ) : null}
      {ack.isError ? (
        <p role="alert" className="text-sm font-semibold text-bad-ink">
          {errorMessage(ack.error)}
        </p>
      ) : null}
    </li>
  );
}

/** Journal des alertes : filtre par statut, bandeau pour les critiques, acquittement selon le rôle. */
export function AlertsLog() {
  const t = useTranslations("alerts");
  const tm = useTranslations("modules");
  const filterId = useId();
  const [status, setStatus] = useState<StatusFilter>("open");
  const alerts = useAlerts(status);
  const me = useMe();
  const rows = alerts.data ?? [];
  const critical = rows.filter((a) => a.severity === "critical" && a.status === "open").length;

  return (
    <ModuleShell title={tm("alerts")} description={t("description")}>
      {critical > 0 ? (
        <p
          role="alert"
          className="flex items-center gap-2 rounded-card bg-bad-bg p-4 font-semibold text-bad-ink"
        >
          <Icon name="bad" size={20} />
          {t("criticalBanner", { count: critical })}
        </p>
      ) : null}
      <div className="flex max-w-sm flex-col gap-1">
        <label htmlFor={filterId} className="text-sm font-semibold">
          {t("filter")}
        </label>
        <select
          id={filterId}
          className="field-input"
          value={status}
          onChange={(e) => setStatus(e.target.value as StatusFilter)}
        >
          {FILTERS.map((f) => (
            <option key={f} value={f}>
              {t(`filters.${f}`)}
            </option>
          ))}
        </select>
      </div>
      <QueryState
        isPending={alerts.isPending}
        error={alerts.error}
        isEmpty={rows.length === 0}
        emptyLabel={t("empty")}
        onRetry={() => void alerts.refetch()}
      >
        <ol role="log" aria-live="polite" aria-label={tm("alerts")} className="flex flex-col gap-3">
          {rows.map((alert) => (
            <AlertItem key={alert.id} alert={alert} canAck={canAckAlerts(me.data, alert.organization_id)} />
          ))}
        </ol>
      </QueryState>
    </ModuleShell>
  );
}

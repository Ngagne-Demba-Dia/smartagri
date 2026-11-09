"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { ApiError } from "@/lib/api";

import { EmptyState } from "./EmptyState";
import { Icon } from "./Icon";
import { SkeletonPage } from "./Skeleton";

/** Codes traduits dans messages/*.json (espace « errors ») ; les autres affichent le message de l'API. */
const KNOWN_CODES = new Set([
  "UNAUTHENTICATED",
  "FORBIDDEN",
  "NOT_FOUND",
  "VALIDATION_ERROR",
  "THRESHOLDS_INVALID",
  "MESSAGE_INVALID",
  "RATE_LIMITED",
  "NETWORK_ERROR",
  "BAD_RESPONSE",
  "LOCATION_REQUIRED",
  "INVALID_CREDENTIALS",
  "UPSTREAM_UNAVAILABLE",
  "WEATHER_UNAVAILABLE",
  "NO_ACTIVE_CYCLE",
  "MODEL_UNAVAILABLE",
  "DEVICE_INACTIVE",
  "CSRF_REJECTED",
  "PAYLOAD_TOO_LARGE",
  "ASSISTANT_UNAVAILABLE",
  "INVALID_BUCKET",
]);

export function useErrorMessage(): (error: unknown) => string {
  const t = useTranslations("errors");
  return (error) => {
    if (error instanceof ApiError) {
      if (KNOWN_CODES.has(error.code)) return t(error.code);
      if (error.message) return error.message;
    }
    return t("generic");
  };
}

export function ErrorNotice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const t = useTranslations("common");
  const message = useErrorMessage();
  return (
    <div role="alert" className="card flex gap-3 border-bad-ink bg-bad-bg">
      <span className="mt-0.5 text-bad-ink">
        <Icon name="bad" />
      </span>
      <div className="flex flex-col items-start gap-2">
        <p className="font-semibold text-bad-ink">{t("errorTitle")}</p>
        <p>{message(error)}</p>
        {onRetry ? (
          <button type="button" className="btn btn-secondary" onClick={onRetry}>
            <Icon name="refresh" size={16} />
            {t("retry")}
          </button>
        ) : null}
      </div>
    </div>
  );
}

interface QueryStateProps {
  isPending: boolean;
  error: unknown;
  isEmpty?: boolean;
  emptyLabel?: string;
  onRetry?: () => void;
  children: ReactNode;
}

/** Les trois états de toute vue de données : chargement, erreur (avec « Réessayer »), vide. */
export function QueryState({
  isPending,
  error,
  isEmpty = false,
  emptyLabel,
  onRetry,
  children,
}: QueryStateProps) {
  const t = useTranslations("common");
  if (error) return <ErrorNotice error={error} onRetry={onRetry} />;
  if (isPending) return <SkeletonPage label={t("loading")} />;
  if (isEmpty) return <EmptyState title={emptyLabel ?? t("empty")} />;
  return <>{children}</>;
}

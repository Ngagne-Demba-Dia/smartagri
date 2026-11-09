"use client";

import { useTranslations } from "next-intl";
import { useCallback } from "react";

import { MISSING, formatDateTime, relativeAge } from "@/lib/format";

/** Libellé « il y a 12 min » traduit ; « — » si l'horodatage est absent ou illisible. */
export function useAgoLabel(): (value: string | null | undefined, now?: Date) => string {
  const t = useTranslations("common");
  return useCallback(
    (value, now) => {
      const age = relativeAge(value, now);
      if (!age) return MISSING;
      if (age.unit === "now") return t("ago.now");
      if (age.unit === "minutes") return t("ago.minutes", { count: age.count });
      if (age.unit === "hours") return t("ago.hours", { count: age.count });
      return t("ago.days", { count: age.count });
    },
    [t],
  );
}

/** Âge relatif, avec la date exacte dans l'élément <time> (lisible au survol et par les lecteurs d'écran). */
export function TimeAgo({ value }: { value: string | null | undefined }) {
  const label = useAgoLabel();
  if (!value) return <span>{MISSING}</span>;
  return (
    <time dateTime={value} title={formatDateTime(value)}>
      {label(value)}
    </time>
  );
}

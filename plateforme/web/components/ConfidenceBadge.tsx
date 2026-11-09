"use client";

import { useTranslations } from "next-intl";

import type { Confidence } from "@/lib/contracts/provenance";

import { ConfidenceText } from "./Provenance";

/** Pastille « Confiance : … » : le texte vient de ConfidenceText, donc jamais un % non calibré. */
export function ConfidenceBadge({ confidence, unit }: { confidence: Confidence; unit?: string }) {
  const t = useTranslations("provenance");
  return (
    <span className="chip flex-wrap">
      <span className="chip-label">{t("confidenceLabel")}</span>
      <span className="font-semibold">
        <ConfidenceText confidence={confidence} unit={unit} />
      </span>
    </span>
  );
}

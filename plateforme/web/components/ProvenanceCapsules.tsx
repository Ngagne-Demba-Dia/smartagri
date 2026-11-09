"use client";

import { useTranslations } from "next-intl";

import { provenanceState, type Provenance, type ProvenanceState } from "@/lib/contracts/provenance";
import type { Tone } from "@/lib/status";

import { ConfidenceBadge } from "./ConfidenceBadge";
import { StatusTag } from "./StatusTag";

const STATE_TONE: Record<ProvenanceState, Tone> = { fresh: "ok", stale: "warn", fallback: "warn" };

/**
 * Provenance en capsules, sur une ligne : état, modèle et confiance. Version compacte du bloc ci-dessus pour
 * les synthèses ; sans bloc, la même phrase « non communiquée » (jamais une provenance supposée).
 */
export function ProvenanceCapsules({ provenance, unit }: { provenance: Provenance | null; unit?: string }) {
  const t = useTranslations("provenance");
  if (!provenance) return <p className="text-xs text-mute">{t("missing")}</p>;
  const state = provenanceState(provenance);
  return (
    <div role="group" aria-label={t("title")} className="flex flex-wrap items-center gap-1.5">
      <StatusTag tone={STATE_TONE[state]} label={t(`state.${state}`)} />
      <span className="chip">{t("model", { name: provenance.model_name, version: provenance.model_version })}</span>
      <ConfidenceBadge confidence={provenance.confidence} unit={unit} />
    </div>
  );
}

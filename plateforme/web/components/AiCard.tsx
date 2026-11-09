"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { provenanceState, type Provenance, type ProvenanceState } from "@/lib/contracts/provenance";
import type { Tone } from "@/lib/status";

import { Icon } from "./Icon";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { ProvenanceNote } from "./Provenance";
import { StatusTag } from "./StatusTag";

const STATE_TONE: Record<ProvenanceState, Tone> = { fresh: "ok", stale: "warn", fallback: "warn" };

/**
 * Carte d'un résultat d'IA : titre, état (à jour / périmé / secours), confiance, contenu, puis le détail de
 * provenance replié (<details>, clavier natif). Sans provenance : « non communiquée », jamais supposée.
 */
export function AiCard({
  title,
  provenance,
  unit,
  children,
}: {
  title: string;
  provenance: Provenance | null;
  unit?: string;
  children: ReactNode;
}) {
  const t = useTranslations("provenance");
  const state = provenance ? provenanceState(provenance) : null;
  return (
    <section className="card card-ai reveal flex min-w-0 flex-col gap-3" aria-label={title}>
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="ai-orb !h-8 !w-8" aria-hidden="true">
            <Icon name="sparkles" size={16} />
          </span>
          <h2 className="text-lg font-semibold">{title}</h2>
        </div>
        {provenance && state ? (
          <div className="flex flex-wrap items-center gap-2">
            <StatusTag tone={STATE_TONE[state]} label={t(`state.${state}`)} />
            <ConfidenceBadge confidence={provenance.confidence} unit={unit} />
          </div>
        ) : null}
      </header>
      <div className="min-w-0">{children}</div>
      <details className="text-sm">
        <summary className="min-h-touch cursor-pointer py-2 font-semibold text-g">{t("title")}</summary>
        <ProvenanceNote provenance={provenance} unit={unit} />
      </details>
    </section>
  );
}

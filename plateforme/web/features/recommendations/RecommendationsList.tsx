"use client";

import { useTranslations } from "next-intl";
import { useCallback, useState } from "react";

import { FieldPicker } from "@/components/FieldPicker";
import { AdvisorAvatar } from "@/components/Illustrations";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { useRecommendations } from "@/services/ai/recommendations";
import { useAllFields, useMe } from "@/hooks/places";
import { canGiveFeedback } from "@/lib/roles";
import type { RecommendationFeedback } from "@/lib/types";

import { RecommendationCard } from "./RecommendationCards";

/**
 * Recommandations IA (module 7) pour la parcelle choisie. Le retour envoyé n'est pas relu par l'API :
 * il n'est mémorisé que pendant la visite de la page.
 */
export function RecommendationsList({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("recommendations");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const me = useMe();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const [sent, setSent] = useState<Readonly<Record<string, RecommendationFeedback>>>({});
  const recommendations = useRecommendations(fieldId);
  const field = all.fields.find((f) => f.id === fieldId);
  const canFeedback = field ? canGiveFeedback(me.data, field.organization_id) : false;
  const rows = recommendations.data ?? [];

  const remember = useCallback(
    (id: string) => (value: RecommendationFeedback) => setSent((prev) => ({ ...prev, [id]: value })),
    [],
  );

  return (
    <ModuleShell title={tm("recommendations")} description={t("description")}>
      <QueryState
        isPending={all.isPending}
        error={all.error}
        isEmpty={all.fields.length === 0}
        emptyLabel={t("noFields")}
        onRetry={all.refetch}
      >
        <FieldPicker farms={all.farms} fields={all.fields} value={fieldId} onChange={setFieldId} />
        <div className="flex items-start gap-3">
          <span className="shrink-0 drop-shadow-md" aria-hidden="true">
            <AdvisorAvatar size={48} />
          </span>
          <p className="advisor-bubble m-0 text-sm text-ink sm:text-base">{t("intro")}</p>
        </div>
        <QueryState
          isPending={recommendations.isPending}
          error={recommendations.error}
          isEmpty={rows.length === 0}
          emptyLabel={t("empty")}
          onRetry={() => void recommendations.refetch()}
        >
          <ul className="stagger flex flex-col gap-4">
            {rows.map((r) => (
              <RecommendationCard
                key={r.id}
                recommendation={r}
                canFeedback={canFeedback}
                sent={sent[r.id]}
                onSent={remember(r.id)}
              />
            ))}
          </ul>
        </QueryState>
      </QueryState>
    </ModuleShell>
  );
}

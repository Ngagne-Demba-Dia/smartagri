"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { AiCard } from "@/components/AiCard";
import { FieldPicker } from "@/components/FieldPicker";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { useAllFields } from "@/hooks/places";
import type { Fertilization } from "@/lib/contracts/field";
import { doseOf, isDegraded, NUTRIENTS, readingKind } from "@/lib/fertilization";
import { formatNumber } from "@/lib/format";
import { useFertilization } from "@/services/ai/fertilization";

const EMPTY = "—";

function Doses({ result }: { result: Fertilization }) {
  const t = useTranslations("fertilization");
  return (
    <dl className="grid gap-3 sm:grid-cols-3">
      {NUTRIENTS.map((nutrient) => {
        const dose = doseOf(result, nutrient);
        return (
          <KpiCard
            key={nutrient}
            label={t(`nutrient.${nutrient}`)}
            value={dose === null ? t("noDose") : t("doseValue", { value: formatNumber(dose, 1) })}
            icon="sprout"
          />
        );
      })}
    </dl>
  );
}

function Reading({ result }: { result: Fertilization }) {
  const t = useTranslations("fertilization");
  const text = t(`reading.${readingKind(result)}`, {
    crop: result.crop ?? EMPTY,
    stage: result.stage ?? EMPTY,
    npkClass: result.npk_class ? t(`npkClass.${result.npk_class}`) : EMPTY,
  });
  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-semibold">{t("readingTitle")}</h3>
      <p className="m-0">{text}</p>
      {isDegraded(result) ? <p className="m-0 text-sm text-warn-ink">{t("readingDegraded")}</p> : null}
      <p className="m-0 text-xs text-mute">{t("readingNote")}</p>
    </div>
  );
}

function Result({ result }: { result: Fertilization }) {
  const t = useTranslations("fertilization");
  return (
    <AiCard title={t("resultTitle")} provenance={result.provenance} unit=" kg/ha">
      <div className="flex flex-col gap-4">
        {result.indicative ? (
          <div role="status" className="flex flex-col gap-1 rounded-card bg-warn-bg p-3 text-warn-ink">
            <StatusTag tone="warn" label={t("indicativeTitle")} />
            <p className="m-0">{result.caveat}</p>
          </div>
        ) : null}
        <Doses result={result} />
        <dl className="m-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-mute">{t("crop")}</dt>
          <dd className="m-0">{result.crop ?? EMPTY}</dd>
          <dt className="text-mute">{t("stage")}</dt>
          <dd className="m-0">{result.stage ?? EMPTY}</dd>
          <dt className="text-mute">{t("npkClassLabel")}</dt>
          <dd className="m-0">{result.npk_class ? t(`npkClass.${result.npk_class}`) : EMPTY}</dd>
        </dl>
        <Reading result={result} />
      </div>
    </AiCard>
  );
}

/** Fertilisation (service 6, doc 18 §5) : doses N, P, K indicatives, classe NPK, lecture du résultat. */
export function FertilizationView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("fertilization");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const query = useFertilization(fieldId);

  return (
    <ModuleShell title={tm("fertilization")} description={t("description")}>
      <QueryState
        isPending={all.isPending}
        error={all.error}
        isEmpty={all.fields.length === 0}
        emptyLabel={t("noFields")}
        onRetry={all.refetch}
      >
        <FieldPicker farms={all.farms} fields={all.fields} value={fieldId} onChange={setFieldId} />
        {fieldId ? (
          <QueryState
            isPending={query.isPending}
            error={query.error}
            isEmpty={!query.data}
            emptyLabel={t("empty")}
            onRetry={() => void query.refetch()}
          >
            {query.data ? <Result result={query.data} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

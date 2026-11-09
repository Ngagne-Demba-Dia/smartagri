"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { AiCard } from "@/components/AiCard";
import { FieldPicker } from "@/components/FieldPicker";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { StatusTag } from "@/components/StatusTag";
import { useAllFields } from "@/hooks/places";
import type { PestRisk } from "@/lib/contracts/field";
import { formatPct } from "@/lib/format";
import {
  groupPests,
  highestLevel,
  probabilityView,
  type PestEntry,
  type PestKind,
  type PestLevel,
} from "@/lib/pests";
import type { Tone } from "@/lib/status";
import { usePestRisk } from "@/services/ai/pest-risk";

const LEVEL_TONE: Record<PestLevel, Tone> = { low: "ok", medium: "warn", high: "bad" };

type Translate = ReturnType<typeof useTranslations>;

function Probability({ p, calibrated, label }: { p: number | null; calibrated: boolean; label: string }) {
  const t = useTranslations("pestRisk");
  const view = probabilityView(p, calibrated);
  const text =
    view.type === "percent" ? formatPct(view.value) : view.type === "uncalibrated" ? t("pUncalibrated") : "—";
  return (
    <span>
      <span className="text-mute">{label} : </span>
      {text}
    </span>
  );
}

function PestRow({ entry, calibrated, name }: { entry: PestEntry; calibrated: boolean; name: string }) {
  const t = useTranslations("pestRisk");
  return (
    <li className="card flex flex-col gap-1">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="m-0 font-semibold">{name}</p>
        <StatusTag tone={LEVEL_TONE[entry.level]} label={t(`level.${entry.level}`)} />
      </div>
      <p className="flex flex-wrap gap-x-4 text-sm">
        <Probability p={entry.p_outbreak_7d} calibrated={calibrated} label={t("p7")} />
        <Probability p={entry.p_outbreak_14d} calibrated={calibrated} label={t("p14")} />
      </p>
      {entry.factors.length > 0 ? (
        <div className="text-sm">
          <p className="text-mute">{t("factors")}</p>
          <ul className="list-disc pl-5">
            {entry.factors.map((factor) => (
              <li key={factor}>{factor}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </li>
  );
}

function Section({
  title,
  emptyLabel,
  entries,
  calibrated,
  nameOf,
}: {
  title: string;
  emptyLabel: string | null;
  entries: readonly PestEntry[];
  calibrated: boolean;
  nameOf: (code: string) => string;
}) {
  if (entries.length === 0 && emptyLabel === null) return null;
  return (
    <section className="flex flex-col gap-2" aria-label={title}>
      <h3 className="font-semibold">{title}</h3>
      {entries.length === 0 ? (
        <p className="text-mute">{emptyLabel}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {entries.map((entry) => (
            <PestRow
              key={entry.pest_code}
              entry={entry}
              calibrated={calibrated}
              name={nameOf(entry.pest_code)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/** Dictionnaire d'affichage (doc 18 §6) : nom et type par code, dans messages/fr.json ; code inconnu → tel quel. */
function dictionary(t: Translate) {
  const known = (code: string) => t.has(`organisms.${code}.name`);
  return {
    nameOf: (code: string) => (known(code) ? t(`organisms.${code}.name`) : code),
    kindOf: (code: string): PestKind | null =>
      known(code) ? (t(`organisms.${code}.kind`) as PestKind) : null,
  };
}

function Result({ risk }: { risk: PestRisk }) {
  const t = useTranslations("pestRisk");
  const { nameOf, kindOf } = dictionary(t);
  const groups = groupPests(risk.pests, kindOf);
  const calibrated = risk.provenance.confidence.calibrated;
  const top = highestLevel(risk.pests);
  return (
    <AiCard title={t("resultTitle")} provenance={risk.provenance}>
      <div className="flex flex-col gap-4">
        {top ? (
          <div role="status" className="flex flex-col gap-1">
            <p className="m-0 text-sm text-mute">{t("highestTitle")}</p>
            <p className="m-0">
              <StatusTag tone={LEVEL_TONE[top]} label={t(`level.${top}`)} />
            </p>
            <p className="m-0 text-xs text-mute">{t("highestNote")}</p>
          </div>
        ) : null}
        <Section
          title={t("pestsTitle")}
          emptyLabel={t("noPests")}
          entries={groups.pest}
          calibrated={calibrated}
          nameOf={nameOf}
        />
        <Section
          title={t("diseasesTitle")}
          emptyLabel={t("noDiseases")}
          entries={groups.disease}
          calibrated={calibrated}
          nameOf={nameOf}
        />
        <Section
          title={t("unclassifiedTitle")}
          emptyLabel={null}
          entries={groups.unclassified}
          calibrated={calibrated}
          nameOf={nameOf}
        />
      </div>
    </AiCard>
  );
}

/** Risques (service 9, doc 18 §6) : niveau et probabilités de foyer par organisme suivi. */
export function PestRiskView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("pestRisk");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const query = usePestRisk(fieldId);

  return (
    <ModuleShell title={tm("pestRisk")} description={t("description")}>
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
            isEmpty={!query.data || query.data.pests.length === 0}
            emptyLabel={t("empty")}
            onRetry={() => void query.refetch()}
          >
            {query.data ? <Result risk={query.data} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

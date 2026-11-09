"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { FieldPicker } from "@/components/FieldPicker";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { Segmented } from "@/components/Segmented";
import { StatusTag } from "@/components/StatusTag";
import { Steps, type StepItem } from "@/components/Steps";
import { useCropCycles } from "@/hooks/field-data";
import { useAllFields } from "@/hooks/places";
import {
  CYCLE_FILTERS,
  countByStatus,
  cycleSteps,
  filterCycles,
  sortedCycles,
  type CycleFilter,
} from "@/lib/crop-cycles";
import { formatDate, formatNumber } from "@/lib/format";
import type { Tone } from "@/lib/status";
import type { CropCycle, CropCycleStatus } from "@/lib/types";

const STATUS_TONE: Record<CropCycleStatus, Tone> = {
  planned: "info",
  active: "ok",
  harvested: "ok",
  abandoned: "warn",
};

function CycleCard({ cycle }: { cycle: CropCycle }) {
  const t = useTranslations("crops");
  const name = cycle.variety ? `${cycle.crop} (${cycle.variety})` : cycle.crop;
  const steps: StepItem[] = cycleSteps(cycle).map((step) => {
    let detail: string | undefined;
    if (step.date) {
      const date = formatDate(step.date);
      detail = step.key === "harvest" && !cycle.harvested_on ? t("expectedOn", { date }) : date;
    }
    return { key: step.key, label: t(`steps.${step.key}`), state: step.state, detail };
  });
  return (
    <li className="card flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="break-words text-lg font-semibold">{name}</h2>
        <StatusTag tone={STATUS_TONE[cycle.status]} label={t(`status.${cycle.status}`)} />
      </div>
      <Steps
        items={steps}
        label={t("stepsLabel", { crop: cycle.crop })}
        stateLabels={{
          done: t("stepState.done"),
          current: t("stepState.current"),
          todo: t("stepState.todo"),
        }}
      />
      {cycle.status === "harvested" ? (
        <p className="text-sm text-mute">
          {cycle.yield_kg === null
            ? t("noYield")
            : t("yieldLine", { value: formatNumber(cycle.yield_kg, 0) })}
        </p>
      ) : null}
    </li>
  );
}

function CycleList({ cycles }: { cycles: readonly CropCycle[] }) {
  const t = useTranslations("crops");
  const [filter, setFilter] = useState<CycleFilter>("all");
  const counts = useMemo(() => countByStatus(cycles), [cycles]);
  const shown = useMemo(() => sortedCycles(filterCycles(cycles, filter)), [cycles, filter]);
  return (
    <div className="flex flex-col gap-4">
      <Segmented
        legend={t("filterLegend")}
        value={filter}
        onChange={setFilter}
        options={CYCLE_FILTERS.map((value) => ({
          value,
          label: t("filterOption", { label: t(`filter.${value}`), count: counts[value] }),
        }))}
      />
      {shown.length === 0 ? (
        <p className="card text-mute">{t("emptyFilter")}</p>
      ) : (
        <ul aria-label={t("listLabel")} className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
          {shown.map((cycle) => (
            <CycleCard key={cycle.id} cycle={cycle} />
          ))}
        </ul>
      )}
    </div>
  );
}

/** Cultures (module 6) : cycles culturaux de la parcelle choisie, du semis à la récolte (lecture seule). */
export function CropsView({ initialFieldId }: { initialFieldId: string | null }) {
  const t = useTranslations("crops");
  const tm = useTranslations("modules");
  const all = useAllFields();
  const [fieldId, setFieldId] = useState<string | null>(initialFieldId);
  const cycles = useCropCycles(fieldId);

  return (
    <ModuleShell title={tm("crops")} description={t("description")} version="V1_1">
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
            isPending={cycles.isPending}
            error={cycles.error}
            isEmpty={!cycles.data || cycles.data.length === 0}
            emptyLabel={t("empty")}
            onRetry={() => void cycles.refetch()}
          >
            {cycles.data ? <CycleList cycles={cycles.data} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

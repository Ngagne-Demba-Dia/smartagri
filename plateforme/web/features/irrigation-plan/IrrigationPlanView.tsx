"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { AiCard } from "@/components/AiCard";
import { DataTable, type Column } from "@/components/DataTable";
import { FarmPicker } from "@/components/FarmPicker";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { QueryState } from "@/components/QueryState";
import { Segmented } from "@/components/Segmented";
import { useAllFields, useFarms } from "@/hooks/places";
import type { IrrigationPlan } from "@/lib/contracts/org";
import { formatClock, formatDate, formatNumber } from "@/lib/format";
import { formatMinutes, planTotals, slotMinutes, sortedSlots, type PlanSlot } from "@/lib/irrigation-plan";
import { isoDay } from "@/lib/windows";
import { useIrrigationPlan } from "@/services/ai/irrigation-plan";

type Day = "today" | "tomorrow";
const DAY_MS = 86_400_000;

function PlanResult({ plan, fieldNames }: { plan: IrrigationPlan; fieldNames: ReadonlyMap<string, string> }) {
  const t = useTranslations("irrigationPlan");
  const slots = sortedSlots(plan.slots);
  const totals = planTotals(slots);
  const columns: Column<PlanSlot>[] = [
    {
      key: "slot",
      header: t("colSlot"),
      cell: (s) => t("slot", { start: formatClock(s.start), end: formatClock(s.end) }),
    },
    {
      key: "field",
      header: t("colField"),
      cell: (s) => fieldNames.get(s.field_id) ?? t("unknownField", { id: s.field_id }),
    },
    {
      key: "pump",
      header: t("colPump"),
      cell: (s) => (t.has(`pumps.${s.pump_id}`) ? t(`pumps.${s.pump_id}`) : s.pump_id),
    },
    { key: "duration", header: t("colDuration"), numeric: true, cell: (s) => formatMinutes(slotMinutes(s)) },
    {
      key: "volume",
      header: t("colVolume"),
      numeric: true,
      cell: (s) => `${formatNumber(s.volume_m3, 1)} m³`,
    },
  ];
  return (
    <AiCard title={t("cardTitle")} provenance={plan.provenance}>
      <div className="flex flex-col gap-4">
        <p className="text-sm text-mute">{t("proposal")}</p>
        <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <KpiCard label={t("kpiVolume")} value={formatNumber(totals.volumeM3, 1)} unit="m³" />
          <KpiCard label={t("kpiDuration")} value={formatMinutes(totals.minutes)} />
          <KpiCard label={t("kpiFields")} value={formatNumber(totals.fields)} />
        </dl>
        <DataTable
          caption={t("tableCaption", { date: formatDate(plan.date) })}
          captionHidden
          columns={columns}
          rows={slots}
          rowKey={(s) => `${s.field_id}-${s.start}`}
        />
      </div>
    </AiCard>
  );
}

/** Planning d'arrosage (service 4, doc 18) : créneaux proposés par exploitation et par jour, à valider par l'exploitant. */
export function IrrigationPlanView() {
  const t = useTranslations("irrigationPlan");
  const tm = useTranslations("modules");
  const farms = useFarms();
  const fields = useAllFields();
  const [selected, setSelected] = useState<string | null>(null);
  const [day, setDay] = useState<Day>("today");
  const [today] = useState(() => new Date());
  const farmId = selected ?? farms.data?.[0]?.id ?? null;
  const date = isoDay(day === "today" ? today : new Date(today.getTime() + DAY_MS));
  const query = useIrrigationPlan(farmId, date);
  const fieldNames = useMemo(() => new Map(fields.fields.map((f) => [f.id, f.name])), [fields.fields]);

  return (
    <ModuleShell title={tm("irrigationPlan")} description={t("description")} version="MVP">
      <QueryState
        isPending={farms.isPending}
        error={farms.error}
        isEmpty={(farms.data?.length ?? 0) === 0}
        emptyLabel={t("noFarms")}
        onRetry={() => void farms.refetch()}
      >
        <div className="flex flex-wrap items-end gap-4">
          <FarmPicker farms={farms.data ?? []} value={farmId} onChange={setSelected} />
          <Segmented
            legend={t("dayLegend")}
            value={day}
            onChange={setDay}
            options={[
              { value: "today", label: t("today") },
              { value: "tomorrow", label: t("tomorrow") },
            ]}
          />
        </div>
        {farmId ? (
          <QueryState
            isPending={query.isPending}
            error={query.error}
            isEmpty={!query.data || query.data.slots.length === 0}
            emptyLabel={t("empty")}
            onRetry={() => void query.refetch()}
          >
            {query.data ? <PlanResult plan={query.data} fieldNames={fieldNames} /> : null}
          </QueryState>
        ) : null}
      </QueryState>
    </ModuleShell>
  );
}

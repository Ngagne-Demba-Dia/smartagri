/** Cultures (module 6) : étapes d'un cycle et filtre par statut, en fonctions pures. */
import type { CropCycle, CropCycleStatus } from "./types";

export type CycleFilter = "all" | CropCycleStatus;
export const CYCLE_FILTERS: readonly CycleFilter[] = ["all", "active", "planned", "harvested", "abandoned"];

export type CycleStepKey = "sow" | "growth" | "harvest";
export type CycleStepState = "done" | "current" | "todo";
export interface CycleStep {
  key: CycleStepKey;
  state: CycleStepState;
  /** Date ISO affichée sous l'étape ; null quand elle n'est pas connue. */
  date: string | null;
}

/**
 * Semis → croissance → récolte, déduits du statut (jamais de la date du jour : un cycle « actif » reste actif
 * tant que le serveur ne le clôt pas). Un cycle abandonné garde son semis fait et s'arrête là.
 */
export function cycleSteps(cycle: CropCycle): CycleStep[] {
  const sown = cycle.planted_on !== null && cycle.status !== "planned";
  const harvested = cycle.status === "harvested";
  const sow: CycleStepState = sown ? "done" : cycle.status === "planned" ? "current" : "todo";
  const growth: CycleStepState = harvested ? "done" : cycle.status === "active" ? "current" : "todo";
  const harvest: CycleStepState = harvested ? "done" : "todo";
  return [
    { key: "sow", state: sow, date: cycle.planted_on },
    { key: "growth", state: growth, date: null },
    { key: "harvest", state: harvest, date: cycle.harvested_on ?? cycle.expected_harvest_on },
  ];
}

export function filterCycles(cycles: readonly CropCycle[], filter: CycleFilter): CropCycle[] {
  return filter === "all" ? [...cycles] : cycles.filter((c) => c.status === filter);
}

const STATUS_ORDER: Record<CropCycleStatus, number> = { active: 0, planned: 1, harvested: 2, abandoned: 3 };

/** Cycles en cours d'abord, puis prévus, récoltés, abandonnés ; à statut égal, le plus récent en premier. */
export function sortedCycles(cycles: readonly CropCycle[]): CropCycle[] {
  return [...cycles].sort(
    (a, b) =>
      STATUS_ORDER[a.status] - STATUS_ORDER[b.status] ||
      (b.planted_on ?? b.created_at).localeCompare(a.planted_on ?? a.created_at),
  );
}

export function countByStatus(cycles: readonly CropCycle[]): Record<CycleFilter, number> {
  const counts: Record<CycleFilter, number> = {
    all: cycles.length,
    active: 0,
    planned: 0,
    harvested: 0,
    abandoned: 0,
  };
  for (const c of cycles) counts[c.status] += 1;
  return counts;
}

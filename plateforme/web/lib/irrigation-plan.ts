/** Planning d'irrigation proposé (service 4) : tri, durées et totaux, calculés sur les créneaux reçus. */
import type { IrrigationPlan } from "./contracts/org";

export type PlanSlot = IrrigationPlan["slots"][number];

export function sortedSlots(slots: readonly PlanSlot[]): PlanSlot[] {
  return [...slots].sort((a, b) => a.start.localeCompare(b.start) || a.field_id.localeCompare(b.field_id));
}

/** Durée d'un créneau en minutes ; 0 si les bornes sont incohérentes. */
export function slotMinutes(slot: PlanSlot): number {
  const ms = Date.parse(slot.end) - Date.parse(slot.start);
  return Number.isFinite(ms) && ms > 0 ? Math.round(ms / 60_000) : 0;
}

export function planTotals(slots: readonly PlanSlot[]): {
  volumeM3: number;
  minutes: number;
  fields: number;
} {
  return {
    volumeM3: slots.reduce((sum, s) => sum + s.volume_m3, 0),
    minutes: slots.reduce((sum, s) => sum + slotMinutes(s), 0),
    fields: new Set(slots.map((s) => s.field_id)).size,
  };
}

/** Durée lisible : « 45 min », « 2 h » ou « 1 h 30 ». */
export function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} h` : `${h} h ${String(m).padStart(2, "0")}`;
}

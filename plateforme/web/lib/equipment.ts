/** Équipements (module 10) : synthèse par état et tri, en fonctions pures. */
import type { Equipment, EquipmentStatus } from "./types";

const STATUS_ORDER: Record<EquipmentStatus, number> = { out_of_service: 0, maintenance: 1, ok: 2 };

export type EquipmentSummary = Record<EquipmentStatus, number> & { total: number };

export function summarizeEquipment(items: readonly Equipment[]): EquipmentSummary {
  const summary: EquipmentSummary = { total: items.length, ok: 0, maintenance: 0, out_of_service: 0 };
  for (const item of items) summary[item.status] += 1;
  return summary;
}

/** Ce qui demande une action (hors service, puis maintenance) passe avant ce qui fonctionne. */
export function sortedEquipment(items: readonly Equipment[]): Equipment[] {
  return [...items].sort(
    (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || a.label.localeCompare(b.label, "fr"),
  );
}

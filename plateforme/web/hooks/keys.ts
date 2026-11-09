/** Clés React Query des données métier ; celles des services d'IA sont dans services/ai/keys.ts. */
import type { RangeKey } from "@/lib/ranges";

/** Taille de page maximale acceptée par l'API (backend MAX_LIMIT). */
export const MAX_LIMIT = 200;

export const qk = {
  me: ["me"] as const,
  farms: ["farms"] as const,
  fields: (farmId: string) => ["farms", farmId, "fields"] as const,
  field: (fieldId: string) => ["fields", fieldId] as const,
  devices: (status: string) => ["devices", { status }] as const,
  device: (deviceId: string) => ["devices", deviceId] as const,
  thresholds: (deviceId: string) => ["devices", deviceId, "thresholds"] as const,
  measurements: (deviceId: string, range: RangeKey) => ["devices", deviceId, "measurements", range] as const,
  cropCycles: (fieldId: string) => ["fields", fieldId, "crop-cycles"] as const,
  campaigns: ["campaigns"] as const,
  equipment: ["equipment"] as const,
};

"use client";

/** Les services d'IA (météo, rendement…) sont dans services/ai ; ici les données métier sans modèle. */
import { useQuery } from "@tanstack/react-query";

import { api, seg } from "@/lib/client";
import type { CropCycle } from "@/lib/types";

import { qk } from "./keys";

/** Module 6 (V1.1). */
export function useCropCycles(fieldId: string | null) {
  return useQuery({
    queryKey: qk.cropCycles(fieldId ?? ""),
    enabled: fieldId !== null,
    queryFn: async ({ signal }) =>
      (await api.get<CropCycle[]>(`/v1/fields/${seg(fieldId ?? "")}/crop-cycles`, undefined, signal)).data,
  });
}

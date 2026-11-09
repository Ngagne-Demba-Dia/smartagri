/** Service 6 — fertilization : GET /v1/fields/{id}/fertilization (proposée) ; « indicatif » tant que non étalonné. */
import { useQuery } from "@tanstack/react-query";

import { FertilizationSchema } from "@/lib/contracts/field";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchFertilization(fieldId: string, options?: CallOptions) {
  const path = `/v1/fields/${seg(fieldId)}/fertilization`;
  return getContract("fertilization", FertilizationSchema, path, undefined, options);
}

export function useFertilization(fieldId: string | null) {
  return useQuery({
    queryKey: aiKeys.fertilization(fieldId ?? ""),
    enabled: fieldId !== null,
    staleTime: staleFor("fertilization"),
    queryFn: ({ signal }) => fetchFertilization(fieldId ?? "", { signal }),
  });
}

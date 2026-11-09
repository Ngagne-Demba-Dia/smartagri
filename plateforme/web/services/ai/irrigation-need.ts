/** Service 3 — irrigation_need : GET /v1/fields/{id}/irrigation-need (proposée), besoin net sur 24 h. */
import { useQuery } from "@tanstack/react-query";

import { IrrigationNeedSchema } from "@/lib/contracts/field";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchIrrigationNeed(fieldId: string, options?: CallOptions) {
  const path = `/v1/fields/${seg(fieldId)}/irrigation-need`;
  return getContract("irrigation_need", IrrigationNeedSchema, path, undefined, options);
}

export function useIrrigationNeed(fieldId: string | null) {
  return useQuery({
    queryKey: aiKeys.irrigationNeed(fieldId ?? ""),
    enabled: fieldId !== null,
    staleTime: staleFor("irrigation_need"),
    queryFn: ({ signal }) => fetchIrrigationNeed(fieldId ?? "", { signal }),
  });
}

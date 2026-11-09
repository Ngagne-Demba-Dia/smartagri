/** Service 9 — pest_risk : GET /v1/fields/{id}/pest-risk (proposée), risque à 7 et 14 jours par ravageur. */
import { useQuery } from "@tanstack/react-query";

import { PestRiskSchema } from "@/lib/contracts/field";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchPestRisk(fieldId: string, options?: CallOptions) {
  return getContract("pest_risk", PestRiskSchema, `/v1/fields/${seg(fieldId)}/pest-risk`, undefined, options);
}

export function usePestRisk(fieldId: string | null) {
  return useQuery({
    queryKey: aiKeys.pestRisk(fieldId ?? ""),
    enabled: fieldId !== null,
    staleTime: staleFor("pest_risk"),
    queryFn: ({ signal }) => fetchPestRisk(fieldId ?? "", { signal }),
  });
}

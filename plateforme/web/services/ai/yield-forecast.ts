/** Service 12 — yield_forecast : GET /v1/fields/{id}/yield-forecast?refresh= (existante ; 404 NO_ACTIVE_CYCLE). */
import { useQuery } from "@tanstack/react-query";

import { YieldForecastSchema } from "@/lib/contracts/field";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchYieldForecast(fieldId: string, options?: CallOptions) {
  const path = `/v1/fields/${seg(fieldId)}/yield-forecast`;
  return getContract("yield_forecast", YieldForecastSchema, path, undefined, options);
}

export function useYieldForecast(fieldId: string | null) {
  return useQuery({
    queryKey: aiKeys.yieldForecast(fieldId ?? ""),
    enabled: fieldId !== null,
    staleTime: staleFor("yield_forecast"),
    queryFn: ({ signal }) => fetchYieldForecast(fieldId ?? "", { signal }),
  });
}

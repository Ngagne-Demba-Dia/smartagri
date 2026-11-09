/** Service 2 — soil_forecast : GET /v1/fields/{id}/soil-forecast?horizons=24,48,72 (proposée), p10/p50/p90. */
import { useQuery } from "@tanstack/react-query";

import { SoilForecastSchema } from "@/lib/contracts/field";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export const SOIL_HORIZONS = [24, 48, 72] as const;

export function fetchSoilForecast(fieldId: string, options?: CallOptions) {
  const query = { horizons: SOIL_HORIZONS.join(",") };
  return getContract("soil_forecast", SoilForecastSchema, `/v1/fields/${seg(fieldId)}/soil-forecast`, query, options);
}

export function useSoilForecast(fieldId: string | null) {
  return useQuery({
    queryKey: aiKeys.soilForecast(fieldId ?? ""),
    enabled: fieldId !== null,
    staleTime: staleFor("soil_forecast"),
    queryFn: ({ signal }) => fetchSoilForecast(fieldId ?? "", { signal }),
  });
}

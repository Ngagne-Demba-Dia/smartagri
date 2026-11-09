/** Service 15 — price_forecast : GET /v1/markets/prices?crop=&market= (proposée), FCFA/kg à 1–4 semaines. */
import { useQuery } from "@tanstack/react-query";

import { PriceForecastSchema } from "@/lib/contracts/org";

import { getContract, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchPriceForecast(crop: string, market: string, options?: CallOptions) {
  return getContract("price_forecast", PriceForecastSchema, "/v1/markets/prices", { crop, market }, options);
}

export function usePriceForecast(crop: string | null, market: string) {
  return useQuery({
    queryKey: aiKeys.prices(crop ?? "", market),
    enabled: crop !== null,
    staleTime: staleFor("price_forecast"),
    queryFn: ({ signal }) => fetchPriceForecast(crop ?? "", market, { signal }),
  });
}

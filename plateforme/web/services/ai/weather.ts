/** Service 1 — weather : GET /v1/fields/{id}/weather?days= (existante ; 400 LOCATION_REQUIRED, 503 WEATHER_UNAVAILABLE). */
import { useQuery } from "@tanstack/react-query";

import { WeatherSchema } from "@/lib/contracts/field";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export const FORECAST_DAYS = 7;

export function fetchWeather(fieldId: string, days: number = FORECAST_DAYS, options?: CallOptions) {
  return getContract("weather", WeatherSchema, `/v1/fields/${seg(fieldId)}/weather`, { days }, options);
}

export function useWeather(fieldId: string | null, days: number = FORECAST_DAYS) {
  return useQuery({
    queryKey: aiKeys.weather(fieldId ?? "", days),
    enabled: fieldId !== null,
    staleTime: staleFor("weather"),
    queryFn: ({ signal }) => fetchWeather(fieldId ?? "", days, { signal }),
  });
}

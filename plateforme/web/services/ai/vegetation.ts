/** Service 11 — vegetation : GET /v1/fields/{id}/vegetation?from=&to= (proposée), NDVI comblé et stade. */
import { useQuery } from "@tanstack/react-query";

import { VegetationSchema } from "@/lib/contracts/field";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchVegetation(fieldId: string, from: string, to: string, options?: CallOptions) {
  const path = `/v1/fields/${seg(fieldId)}/vegetation`;
  return getContract("vegetation", VegetationSchema, path, { from, to }, options);
}

export function useVegetation(fieldId: string | null, from: string, to: string) {
  return useQuery({
    queryKey: aiKeys.vegetation(fieldId ?? "", from, to),
    enabled: fieldId !== null,
    staleTime: staleFor("vegetation"),
    queryFn: ({ signal }) => fetchVegetation(fieldId ?? "", from, to, { signal }),
  });
}

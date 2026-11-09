/** Service 10 — trap_counts : GET /v1/devices/{id}/trap-counts?from=&to= (proposée), comptage par photo de piège. */
import { useQuery } from "@tanstack/react-query";

import { TrapCountsSchema } from "@/lib/contracts/device";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchTrapCounts(deviceId: string, from: string, to: string, options?: CallOptions) {
  const path = `/v1/devices/${seg(deviceId)}/trap-counts`;
  return getContract("trap_counts", TrapCountsSchema, path, { from, to }, options);
}

export function useTrapCounts(deviceId: string | null, from: string, to: string) {
  return useQuery({
    queryKey: aiKeys.trapCounts(deviceId ?? "", from, to),
    enabled: deviceId !== null,
    staleTime: staleFor("trap_counts"),
    queryFn: ({ signal }) => fetchTrapCounts(deviceId ?? "", from, to, { signal }),
  });
}

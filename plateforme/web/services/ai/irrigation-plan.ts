/** Service 4 — irrigation_plan : GET /v1/farms/{farm_id}/irrigation-plan?date= (proposée), créneaux par pompe. */
import { useQuery } from "@tanstack/react-query";

import { IrrigationPlanSchema } from "@/lib/contracts/org";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchIrrigationPlan(farmId: string, date: string, options?: CallOptions) {
  const path = `/v1/farms/${seg(farmId)}/irrigation-plan`;
  return getContract("irrigation_plan", IrrigationPlanSchema, path, { date }, options);
}

export function useIrrigationPlan(farmId: string | null, date: string) {
  return useQuery({
    queryKey: aiKeys.irrigationPlan(farmId ?? "", date),
    enabled: farmId !== null,
    staleTime: staleFor("irrigation_plan"),
    queryFn: ({ signal }) => fetchIrrigationPlan(farmId ?? "", date, { signal }),
  });
}

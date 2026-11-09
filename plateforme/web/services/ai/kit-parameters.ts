/**
 * Service 7 — kit_parameters : GET /v1/devices/{id}/parameters (proposée). Les seuils restent « seuil conseillé »
 * tant que l'utilisateur ne les applique pas par PUT /v1/devices/{id}/thresholds (existante, hooks/devices.ts).
 */
import { useQuery } from "@tanstack/react-query";

import { KitParametersSchema, PARAM_VALIDITY_DAYS, type ParameterBlock } from "@/lib/contracts/device";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

const DAY_MS = 86_400_000;

export function fetchKitParameters(deviceId: string, options?: CallOptions) {
  const path = `/v1/devices/${seg(deviceId)}/parameters`;
  return getContract("kit_parameters", KitParametersSchema, path, undefined, options);
}

/** Un bloc est « périmé » au-delà de sa durée de validité (doc 16 §6.1), quelle que soit sa source. */
export function isBlockExpired(block: ParameterBlock, computedAt: string, now: Date = new Date()): boolean {
  const age = now.getTime() - new Date(computedAt).getTime();
  return age > PARAM_VALIDITY_DAYS[block] * DAY_MS;
}

export function useKitParameters(deviceId: string | null) {
  return useQuery({
    queryKey: aiKeys.kitParameters(deviceId ?? ""),
    enabled: deviceId !== null,
    staleTime: staleFor("kit_parameters"),
    queryFn: ({ signal }) => fetchKitParameters(deviceId ?? "", { signal }),
  });
}

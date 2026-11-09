/**
 * Service 13 — device_health : GET /v1/devices/{id}/health (proposée), GET /v1/alerts et
 * POST /v1/alerts/{id}/ack (existantes). Les alertes sont relues chaque minute.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { AlertListSchema, AlertSchema, DeviceHealthSchema } from "@/lib/contracts/device";

import { getContract, postContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

const ALERTS_REFETCH_MS = 60_000;
const ALERTS_LIMIT = 200;

export type AlertFilter = "open" | "acknowledged" | "resolved" | "all";

export function fetchDeviceHealth(deviceId: string, options?: CallOptions) {
  const path = `/v1/devices/${seg(deviceId)}/health`;
  return getContract("device_health", DeviceHealthSchema, path, undefined, options);
}

export function fetchAlerts(status: AlertFilter = "open", options?: CallOptions) {
  const query = { limit: ALERTS_LIMIT, status: status === "all" ? undefined : status };
  return getContract("device_health", AlertListSchema, "/v1/alerts", query, options);
}

export function ackAlert(alertId: string, options?: CallOptions) {
  return postContract("device_health", AlertSchema, `/v1/alerts/${seg(alertId)}/ack`, undefined, options);
}

export function useDeviceHealth(deviceId: string | null) {
  return useQuery({
    queryKey: aiKeys.deviceHealth(deviceId ?? ""),
    enabled: deviceId !== null,
    staleTime: staleFor("device_health"),
    queryFn: ({ signal }) => fetchDeviceHealth(deviceId ?? "", { signal }),
  });
}

export function useAlerts(status: AlertFilter = "open") {
  return useQuery({
    queryKey: aiKeys.alerts(status),
    queryFn: ({ signal }) => fetchAlerts(status, { signal }),
    refetchInterval: ALERTS_REFETCH_MS,
  });
}

export function useAckAlert() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => ackAlert(alertId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["alerts"] });
      void client.invalidateQueries({ queryKey: ["farms"] });
    },
  });
}

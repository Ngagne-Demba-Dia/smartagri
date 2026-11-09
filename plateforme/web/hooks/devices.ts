"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, seg } from "@/lib/client";
import { rangeWindow, type RangeKey } from "@/lib/ranges";
import type { Device, DeviceDetail, DeviceStatus, MeasurementSeries, ThresholdState, ThresholdsInput } from "@/lib/types";

import { MAX_LIMIT, qk } from "./keys";

/** GET /v1/devices?status= — pas de filtre par parcelle côté API : le filtrage se fait ici. */
export function useDevices(status: DeviceStatus = "active") {
  return useQuery({
    queryKey: qk.devices(status),
    queryFn: async ({ signal }) => (await api.get<Device[]>("/v1/devices", { status, limit: MAX_LIMIT }, signal)).data,
  });
}

export function useDevice(deviceId: string | null) {
  return useQuery({
    queryKey: qk.device(deviceId ?? ""),
    enabled: deviceId !== null,
    queryFn: async ({ signal }) =>
      (await api.get<DeviceDetail>(`/v1/devices/${seg(deviceId ?? "")}`, undefined, signal)).data,
  });
}

/** GET /v1/devices/{id}/measurements?from=&to=&bucket= ; la fenêtre est recalculée à chaque chargement. */
export function useMeasurements(deviceId: string | null, range: RangeKey) {
  return useQuery({
    queryKey: qk.measurements(deviceId ?? "", range),
    enabled: deviceId !== null,
    queryFn: async ({ signal }) => {
      const { from, to, bucket } = rangeWindow(range);
      const path = `/v1/devices/${seg(deviceId ?? "")}/measurements`;
      return (await api.get<MeasurementSeries>(path, { from, to, bucket }, signal)).data;
    },
  });
}

/**
 * PUT /v1/devices/{id}/thresholds {start, stop}. Le kit n'est pas joignable depuis le serveur (ADR 007) :
 * la valeur reste « pending » jusqu'au passage du téléphone relais, qui l'envoie au kit (POST /seuils).
 */
export function useUpdateThresholds(deviceId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (input: ThresholdsInput) =>
      (await api.put<ThresholdState>(`/v1/devices/${seg(deviceId)}/thresholds`, input)).data,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["devices"] });
      void client.invalidateQueries({ queryKey: ["farms"] });
    },
  });
}

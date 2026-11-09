"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/client";
import type { Campaign, Equipment } from "@/lib/types";

import { MAX_LIMIT, qk } from "./keys";

/** Module 11 (V1.1). */
export function useCampaigns() {
  return useQuery({
    queryKey: qk.campaigns,
    queryFn: async ({ signal }) => (await api.get<Campaign[]>("/v1/campaigns", { limit: MAX_LIMIT }, signal)).data,
  });
}

/** Module 10 (V1.1). */
export function useEquipment() {
  return useQuery({
    queryKey: qk.equipment,
    queryFn: async ({ signal }) => (await api.get<Equipment[]>("/v1/equipment", { limit: MAX_LIMIT }, signal)).data,
  });
}

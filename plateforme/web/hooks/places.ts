"use client";

import { useQueries, useQuery } from "@tanstack/react-query";

import { api, seg } from "@/lib/client";
import type { Farm, Field, FieldDetail, Me } from "@/lib/types";

import { MAX_LIMIT, qk } from "./keys";

const ME_STALE_MS = 5 * 60_000;

export function useMe() {
  return useQuery({
    queryKey: qk.me,
    queryFn: async ({ signal }) => (await api.get<Me>("/v1/me", undefined, signal)).data,
    staleTime: ME_STALE_MS,
  });
}

/** GET /v1/farms — première page seulement (200 exploitations) : suffisant pour une coopérative pilote. */
export function useFarms() {
  return useQuery({
    queryKey: qk.farms,
    queryFn: async ({ signal }) => (await api.get<Farm[]>("/v1/farms", { limit: MAX_LIMIT }, signal)).data,
  });
}

export function useFields(farmId: string | null) {
  return useQuery({
    queryKey: qk.fields(farmId ?? ""),
    enabled: farmId !== null,
    queryFn: async ({ signal }) =>
      (await api.get<Field[]>(`/v1/farms/${seg(farmId ?? "")}/fields`, { limit: MAX_LIMIT }, signal)).data,
  });
}

/**
 * Toutes les parcelles visibles : une requête par exploitation (pas de GET /v1/fields global côté API).
 * Le résultat combiné reste en chargement tant qu'une exploitation n'a pas répondu.
 */
export function useAllFields() {
  const farms = useFarms();
  const list = farms.data ?? [];
  return useQueries({
    queries: list.map((farm) => ({
      queryKey: qk.fields(farm.id),
      queryFn: async ({ signal }: { signal: AbortSignal }) =>
        (await api.get<Field[]>(`/v1/farms/${seg(farm.id)}/fields`, { limit: MAX_LIMIT }, signal)).data,
    })),
    combine: (results) => ({
      farms: list,
      fields: results.flatMap((r) => r.data ?? []),
      isPending: farms.isPending || results.some((r) => r.isPending),
      error: farms.error ?? results.find((r) => r.error)?.error ?? null,
      refetch: () => {
        void farms.refetch();
        results.forEach((r) => void r.refetch());
      },
    }),
  });
}

/** GET /v1/fields/{id} : parcelle + cycle actif ; 404 si elle n'appartient pas à l'organisation. */
export function useField(fieldId: string) {
  return useQuery({
    queryKey: qk.field(fieldId),
    queryFn: async ({ signal }) => (await api.get<FieldDetail>(`/v1/fields/${seg(fieldId)}`, undefined, signal)).data,
  });
}

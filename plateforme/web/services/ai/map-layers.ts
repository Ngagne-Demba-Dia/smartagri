/**
 * Service 18 — map_layers : GET /v1/farms/{farm_id}/map (existante) et ?layers=crop_type,salinity (proposée).
 * Une requête par exploitation ; le résultat combiné reste en chargement tant qu'une carte manque.
 */
import { useQueries, useQuery } from "@tanstack/react-query";

import { MapLayersSchema, type MapLayer, type MapLayersView } from "@/lib/contracts/org";
import { useFarms } from "@/hooks/places";

import { getContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export function fetchFarmMap(farmId: string, layers: readonly MapLayer[] = [], options?: CallOptions) {
  const query = { layers: layers.length > 0 ? layers.join(",") : undefined };
  return getContract("map_layers", MapLayersSchema, `/v1/farms/${seg(farmId)}/map`, query, options);
}

export interface FarmMapEntry {
  farmId: string;
  farmName: string;
  map: MapLayersView;
}

export function useFarmMaps(layers: readonly MapLayer[] = []) {
  const farms = useFarms();
  const list = farms.data ?? [];
  const layerKey = layers.join(",");
  return useQueries({
    queries: list.map((farm) => ({
      queryKey: aiKeys.mapLayers(farm.id, layerKey),
      staleTime: staleFor("map_layers"),
      queryFn: ({ signal }: { signal: AbortSignal }) => fetchFarmMap(farm.id, layers, { signal }),
    })),
    combine: (results) => ({
      farms: list,
      maps: results.flatMap((r, i): FarmMapEntry[] => {
        const farm = list[i];
        return r.data && farm ? [{ farmId: farm.id, farmName: farm.name, map: r.data }] : [];
      }),
      isPending: farms.isPending || results.some((r) => r.isPending),
      error: farms.error ?? results.find((r) => r.error)?.error ?? null,
      dataUpdatedAt: Math.max(0, ...results.map((r) => r.dataUpdatedAt)),
      refetch: () => {
        void farms.refetch();
        results.forEach((r) => void r.refetch());
      },
    }),
  });
}

/**
 * Couches d'une seule exploitation (carte Leaflet) : inactive sans exploitation ou sans couche demandée,
 * la carte de base venant alors de useFarmMaps(). Même clé de cache que useFarmMaps(layers).
 */
export function useFarmMapLayers(farmId: string | null, layers: readonly MapLayer[]) {
  return useQuery({
    queryKey: aiKeys.mapLayers(farmId ?? "", layers.join(",")),
    enabled: farmId !== null && layers.length > 0,
    staleTime: staleFor("map_layers"),
    queryFn: ({ signal }) => fetchFarmMap(farmId ?? "", layers, { signal }),
  });
}

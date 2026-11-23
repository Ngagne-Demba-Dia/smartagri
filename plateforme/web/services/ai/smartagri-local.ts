/** Hooks React Query vers les endpoints `/v1/ai/*` (runtime local `smartagri-ai`). */
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/client";
import {
  askAiOrchestrator,
  getAiHealth,
  interpretWolofIntent,
  predictDiseaseAi,
  predictPriceAi,
  predictYieldAi,
} from "@/lib/ai";

export const useSmartAgriAiHealth = () =>
  useQuery({
    queryKey: ["smartagri-local", "health"],
    queryFn: async () => (await getAiHealth(api)).data,
    retry: false,
  });

export const useAskSmartAgriAi = () =>
  useMutation({
    mutationFn: async (payload: { query: string; features?: Record<string, unknown>; crop?: string }) =>
      (await askAiOrchestrator(api, payload)).data,
  });

export const useInterpretWolof = () =>
  useMutation({
    mutationFn: async (text: string) => (await interpretWolofIntent(api, text)).data,
  });

export const usePredictYieldAi = () =>
  useMutation({
    mutationFn: async (payload: { crop: string; region: string; year?: number; area_ha?: number }) =>
      (await predictYieldAi(api, payload)).data,
  });

export const usePredictPriceAi = () =>
  useMutation({
    mutationFn: async (payload: { commodity: string; market: string; region: string; year?: number; month?: number }) =>
      (await predictPriceAi(api, payload)).data,
  });

export const usePredictDiseaseAi = () =>
  useMutation({
    mutationFn: async (imagePath: string) => (await predictDiseaseAi(api, imagePath)).data,
  });

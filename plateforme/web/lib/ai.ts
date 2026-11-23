/** Client typé Frontend → BFF (`/api/v1/ai/*`) vers le runtime `smartagri-ai`. */
import type { ApiClient } from "./api";

export interface AiServiceResponse<T = Record<string, unknown>> {
  service: string;
  values: T;
  confidence: number;
  confidence_level: string;
  warnings: string[];
  abstained: boolean;
  abstention_reason: string;
  latency_ms: number;
}

export interface AiOrchestratorResponse {
  intent: string;
  answer: string;
  confidence: number;
  confidence_level: string;
  components_called: string[];
  latency_ms: number;
  warnings: string[];
  abstentions: string[];
  escalate: boolean;
}

export const getAiHealth = (api: ApiClient) =>
  api.get<Record<string, unknown>>("/v1/ai/health");

export const predictSoilAi = (api: ApiClient, features: Record<string, number>) =>
  api.post<AiServiceResponse>("/v1/ai/soil/predict", { features });

export const predictYieldAi = (
  api: ApiClient,
  payload: { crop: string; region: string; year?: number; area_ha?: number },
) => api.post<AiServiceResponse>("/v1/ai/yield/predict", payload);

export const predictPriceAi = (
  api: ApiClient,
  payload: { commodity: string; market: string; region: string; year?: number; month?: number },
) => api.post<AiServiceResponse>("/v1/ai/price/predict", payload);

export const getMarketClustersAi = (api: ApiClient, topN = 5) =>
  api.get<AiServiceResponse>("/v1/ai/market/clusters", { top_n: topN });

export const predictDiseaseAi = (api: ApiClient, imagePath: string) =>
  api.post<AiServiceResponse>("/v1/ai/disease/predict", { image_path: imagePath });

export const askAiOrchestrator = (
  api: ApiClient,
  payload: { query: string; features?: Record<string, unknown>; crop?: string },
) => api.post<AiOrchestratorResponse>("/v1/ai/orchestrator/ask", payload);

export const interpretWolofIntent = (api: ApiClient, text: string) =>
  api.post<{ original_wo: string; normalized_fr: string; detected_crop: string }>(
    "/v1/ai/voice/intent",
    { text },
  );

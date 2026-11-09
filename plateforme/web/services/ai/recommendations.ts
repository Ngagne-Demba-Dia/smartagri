/**
 * Service 5 — recommendations : GET /v1/fields/{id}/recommendations et POST /v1/recommendations/{id}/feedback
 * (existantes). La vue renvoyée après un retour ne porte pas ce retour : l'écran le garde localement.
 */
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  FEEDBACK_VALUES,
  FeedbackInputSchema,
  RecommendationListSchema,
  RecommendationSchema,
} from "@/lib/contracts/field";

import { getContract, postContract, seg, staleFor, type CallOptions } from "./client";
import { aiKeys } from "./keys";

export type FeedbackValue = (typeof FEEDBACK_VALUES)[number];

export function fetchRecommendations(fieldId: string, options?: CallOptions) {
  const path = `/v1/fields/${seg(fieldId)}/recommendations`;
  return getContract("recommendations", RecommendationListSchema, path, undefined, options);
}

export function sendRecommendationFeedback(id: string, feedback: FeedbackValue, options?: CallOptions) {
  const body = FeedbackInputSchema.parse({ feedback });
  const path = `/v1/recommendations/${seg(id)}/feedback`;
  return postContract("recommendations", RecommendationSchema, path, body, options);
}

export function useRecommendations(fieldId: string | null) {
  return useQuery({
    queryKey: aiKeys.recommendations(fieldId ?? ""),
    enabled: fieldId !== null,
    staleTime: staleFor("recommendations"),
    queryFn: ({ signal }) => fetchRecommendations(fieldId ?? "", { signal }),
  });
}

export function useRecommendationFeedback() {
  return useMutation({
    mutationFn: ({ id, feedback }: { id: string; feedback: FeedbackValue }) => sendRecommendationFeedback(id, feedback),
  });
}

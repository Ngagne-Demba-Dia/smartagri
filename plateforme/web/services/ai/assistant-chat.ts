/**
 * Service 16 — assistant_chat : POST /v1/assistant/chat (existante ; 503 ASSISTANT_UNAVAILABLE,
 * 502 ASSISTANT_BAD_RESPONSE, 429 RATE_LIMITED). Réponse en texte brut, affichée sans interprétation HTML.
 */
import { useMutation } from "@tanstack/react-query";

import { ChatInputSchema, ChatResultSchema, type ChatRequest } from "@/lib/contracts/assistant";

import { postContract, type CallOptions } from "./client";

export function sendChat(input: ChatRequest, options?: CallOptions) {
  const body = ChatInputSchema.parse(input);
  return postContract("assistant_chat", ChatResultSchema, "/v1/assistant/chat", body, options);
}

export function useChat() {
  return useMutation({ mutationFn: (input: ChatRequest) => sendChat(input) });
}

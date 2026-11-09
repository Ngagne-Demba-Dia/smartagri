/** Service 17 — assistant_transcribe : POST /v1/assistant/transcribe (proposée), 60 s au plus, wo/ff/fr. */
import { useMutation } from "@tanstack/react-query";

import { TranscribeInputSchema, TranscriptionSchema, type TranscribeInput } from "@/lib/contracts/assistant";

import { postContract, type CallOptions } from "./client";

export function transcribeAudio(input: TranscribeInput, options?: CallOptions) {
  const body = TranscribeInputSchema.parse(input);
  return postContract("assistant_transcribe", TranscriptionSchema, "/v1/assistant/transcribe", body, options);
}

export function useTranscribe() {
  return useMutation({ mutationFn: (input: TranscribeInput) => transcribeAudio(input) });
}

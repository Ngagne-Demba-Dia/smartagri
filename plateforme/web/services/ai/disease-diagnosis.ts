/**
 * Service 8 — disease_diagnosis : POST /v1/diagnoses/analyze (proposée). Abstention sous 0,7 ;
 * 413 PAYLOAD_TOO_LARGE si l'image dépasse la limite du BFF. L'enregistrement (POST /v1/diagnoses, existante)
 * reste du ressort du téléphone ou du kit caméra.
 */
import { useMutation } from "@tanstack/react-query";

import {
  DiagnosisInputSchema,
  DiagnosisSchema,
  UPLOAD_MAX_RAW_BYTES,
  type DiagnosisInput,
} from "@/lib/contracts/assistant";
import { ApiError } from "@/lib/api";

import { postContract, type CallOptions } from "./client";

/** Taille décodée approximative d'une chaîne base64 (sans en-tête data:). */
export function base64Bytes(b64: string): number {
  const padding = b64.endsWith("==") ? 2 : b64.endsWith("=") ? 1 : 0;
  return Math.floor((b64.length * 3) / 4) - padding;
}

export function analyzeDiagnosis(input: DiagnosisInput, options?: CallOptions) {
  const body = DiagnosisInputSchema.parse(input);
  if (base64Bytes(body.image_base64) > UPLOAD_MAX_RAW_BYTES) {
    return Promise.reject(new ApiError("PAYLOAD_TOO_LARGE", "Image trop lourde.", 413));
  }
  return postContract("disease_diagnosis", DiagnosisSchema, "/v1/diagnoses/analyze", body, options);
}

export function useDiagnosis() {
  return useMutation({ mutationFn: (input: DiagnosisInput) => analyzeDiagnosis(input) });
}

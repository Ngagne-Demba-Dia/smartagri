/**
 * Contrats de l'assistant et de la vision (doc 16 §9.3–9.4, services 8, 16 et 17).
 * Le proxy du BFF n'accepte que du JSON de 256 Kio au plus : image et audio partent en base64
 * (PAYLOAD_TOO_LARGE, 413, au-delà), après réduction de l'image côté navigateur.
 */
import { z } from "zod";

import { OptionalProvenance, ProvenanceSchema, isoDateTime } from "./provenance";

const id = z.string().min(1);
export const UPLOAD_MAX_BYTES = 256 * 1024;
/** Marge pour les autres champs JSON et le surcoût base64 (4/3). */
export const UPLOAD_MAX_RAW_BYTES = Math.floor(((UPLOAD_MAX_BYTES - 2048) * 3) / 4);
export const AUDIO_MAX_SECONDS = 60;
export const ASSISTANT_LANGUAGES = ["wo", "ff", "fr"] as const;

/* 8. disease_diagnosis — POST /v1/diagnoses/analyze (proposée) ; POST /v1/diagnoses (existante) enregistre */
export const DiagnosisInputSchema = z
  .object({
    image_base64: z.string().min(1),
    content_type: z.enum(["image/jpeg", "image/png", "image/webp"]),
    field_id: id.nullable(),
    device_id: id.nullable(),
    captured_at: isoDateTime,
  })
  .refine((v) => v.field_id !== null || v.device_id !== null, { message: "field_id ou device_id obligatoire." });

export const DiagnosisSchema = z.object({
  /** null : analyse seule ; l'enregistrement passe par POST /v1/diagnoses (téléphone ou kit caméra). */
  id: id.nullable(),
  label: z.enum(["healthy", "suspect", "sick"]),
  disease_code: z.string().nullable(),
  top3: z.array(z.object({ code: z.string(), probability: z.number().min(0).max(1) })).max(3),
  abstained: z.boolean(),
  captured_at: isoDateTime,
  provenance: ProvenanceSchema,
});

/* 16. assistant_chat — POST /v1/assistant/chat (existante) ; citations et refus motivé ajoutés */
export const ChatInputSchema = z.object({
  message: z.string().trim().min(1).max(2000),
  conversation_id: z.string().nullable().optional(),
  organization_id: z.string().nullable().optional(),
  locale: z.enum(ASSISTANT_LANGUAGES).nullable().optional(),
});

export const ChatResultSchema = z.object({
  conversation_id: id,
  reply: z.string(),
  stop_reason: z.string().nullable(),
  tools_used: z.array(z.string()),
  truncated: z.boolean(),
  limit_reached: z.boolean(),
  model: z.string().nullable(),
  fallback_used: z.boolean(),
  citations: z.array(z.object({ title: z.string(), source: z.string(), excerpt: z.string().nullable() })).default([]),
  refusal: z.object({ reason: z.string() }).nullable().default(null),
  provenance: OptionalProvenance,
});

/* 17. assistant_transcribe — POST /v1/assistant/transcribe (proposée) ; 60 s au plus, wo/ff/fr */
export const TranscribeInputSchema = z.object({
  audio_base64: z.string().min(1),
  content_type: z.string().regex(/^audio\/[a-z0-9.+-]+(;.*)?$/i),
  duration_s: z.number().positive().max(AUDIO_MAX_SECONDS),
  language_hint: z.enum(ASSISTANT_LANGUAGES).nullable(),
});

export const TranscriptionSchema = z.object({
  text: z.string(),
  language: z.enum(ASSISTANT_LANGUAGES),
  duration_s: z.number().min(0),
  provenance: ProvenanceSchema,
});

export type DiagnosisInput = z.infer<typeof DiagnosisInputSchema>;
export type Diagnosis = z.infer<typeof DiagnosisSchema>;
export type ChatRequest = z.infer<typeof ChatInputSchema>;
export type ChatReply = z.infer<typeof ChatResultSchema>;
export type TranscribeInput = z.infer<typeof TranscribeInputSchema>;
export type Transcription = z.infer<typeof TranscriptionSchema>;
export type AssistantLanguage = (typeof ASSISTANT_LANGUAGES)[number];

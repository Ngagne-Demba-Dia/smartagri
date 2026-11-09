/**
 * Enveloppe commune (CONVENTIONS §5, doc 16 §9.1) et validation des réponses par contrat.
 * Une réponse simulée porte meta.mock = true ; la forme, les codes et les noms de champs sont ceux
 * du contrat (doc 16 §9.5), pour que la bascule vers l'API réelle ne touche aucun composant.
 */
import { z } from "zod";

import { ApiError } from "@/lib/api";

export const ApiErrorBodySchema = z.object({
  code: z.string().min(1),
  message: z.string(),
  details: z.record(z.string(), z.unknown()).optional(),
});

export const MetaSchema = z
  .object({
    mock: z.boolean().optional(),
    scenario: z.string().optional(),
    page: z.number().optional(),
    limit: z.number().optional(),
    total: z.number().optional(),
  })
  .catchall(z.unknown());

export function envelopeSchema<T extends z.ZodType>(data: T) {
  return z.object({
    success: z.boolean(),
    data: data.nullable(),
    error: ApiErrorBodySchema.nullable(),
    meta: MetaSchema.nullable(),
  });
}

/** Codes d'erreur des services d'IA (doc 16 §9.5), en plus de ceux de CONVENTIONS §5. */
export const AI_ERROR_STATUS = {
  MODEL_UNAVAILABLE: 503,
  WEATHER_UNAVAILABLE: 503,
  NO_ACTIVE_CYCLE: 404,
  ASSISTANT_UNAVAILABLE: 503,
  ASSISTANT_BAD_RESPONSE: 502,
  RATE_LIMITED: 429,
  NOT_FOUND: 404,
  THRESHOLDS_INVALID: 400,
  VALIDATION_ERROR: 422,
  PAYLOAD_TOO_LARGE: 413,
  NOT_READY: 503,
} as const;

export type AiErrorCode = keyof typeof AI_ERROR_STATUS;

/**
 * Valide la donnée reçue contre son schéma. Une réponse non conforme lève ApiError("BAD_RESPONSE") :
 * l'écran affiche une erreur au lieu d'un chiffre faux.
 */
export function parseContract<T extends z.ZodType>(schema: T, data: unknown, service: string): z.output<T> {
  const result = schema.safeParse(data);
  if (result.success) return result.data;
  const issues = result.error.issues.slice(0, 5).map((i) => `${i.path.join(".") || "(racine)"} : ${i.message}`);
  throw new ApiError("BAD_RESPONSE", "Réponse du serveur non conforme au contrat.", 502, { service, issues });
}

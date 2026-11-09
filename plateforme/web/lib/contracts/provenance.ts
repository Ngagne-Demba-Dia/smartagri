/**
 * Bloc de provenance de doc 16 §9.2 (baseline v1, gelée) : tout résultat d'IA le porte.
 * Exemple du contrat :
 *   {"model_name":"irr_need_24h","model_version":"3","source":"agriml","fallback_step":0,
 *    "computed_at":"2027-03-02T06:00:00Z","data_as_of":"2027-03-02T05:00:00Z","stale":false,
 *    "confidence":{"kind":"interval","value":null,"p10":4.1,"p90":7.9,"calibrated":true}}
 * Règles d'affichage (doc 16 §6.3 et §9.5) : une confiance non calibrée n'est jamais montrée en %,
 * une valeur en cache n'est jamais présentée comme fraîche, fallback_step > 0 = valeur de secours.
 */
import { z } from "zod";

export const PROVENANCE_SOURCES = ["agriml", "octopus", "rules"] as const;
export const CONFIDENCE_KINDS = ["probability", "interval", "class_probability", "none"] as const;
/** Chaîne de repli : bundle (0) → lot OctOpus (1) → règles (2) → MODEL_UNAVAILABLE. */
export const MAX_FALLBACK_STEP = 2;

export const isoDateTime = z.iso.datetime({ offset: true });
export const isoDate = z.iso.date();

export const ConfidenceSchema = z
  .object({
    kind: z.enum(CONFIDENCE_KINDS),
    value: z.number().min(0).max(1).nullable(),
    p10: z.number().nullable().default(null),
    p90: z.number().nullable().default(null),
    calibrated: z.boolean(),
  })
  .superRefine((c, ctx) => {
    if (c.kind === "none" && (c.value !== null || c.p10 !== null || c.p90 !== null)) {
      ctx.addIssue({ code: "custom", message: "kind « none » : aucune valeur de confiance." });
    }
    if (c.kind === "interval" && (c.p10 === null || c.p90 === null || c.p10 > c.p90)) {
      ctx.addIssue({ code: "custom", message: "kind « interval » : p10 ≤ p90 obligatoires." });
    }
  });

export const ProvenanceSchema = z.object({
  model_name: z.string().min(1),
  model_version: z.string().min(1),
  source: z.enum(PROVENANCE_SOURCES),
  fallback_step: z.number().int().min(0).max(MAX_FALLBACK_STEP),
  computed_at: isoDateTime,
  data_as_of: isoDateTime.nullable(),
  stale: z.boolean(),
  confidence: ConfidenceSchema,
});

/**
 * Routes existantes (doc 16 §9.1 : leur forme ne change pas) : la provenance s'y ajoute en v1.1.
 * Tant que l'API ne l'envoie pas, elle vaut null et l'écran dit « provenance non communiquée ».
 */
export const OptionalProvenance = ProvenanceSchema.nullable().default(null);

export type Confidence = z.infer<typeof ConfidenceSchema>;
export type Provenance = z.infer<typeof ProvenanceSchema>;
export type ProvenanceSource = Provenance["source"];

/** États d'affichage de doc 16 §9.5 (l'abstention et le vide sont portés par la charge utile). */
export type ProvenanceState = "fresh" | "stale" | "fallback";

export function provenanceState(p: Provenance): ProvenanceState {
  if (p.fallback_step > 0) return "fallback";
  return p.stale ? "stale" : "fresh";
}

export type ConfidenceView =
  | { type: "percent"; value: number }
  | { type: "interval"; p10: number; p90: number; calibrated: boolean }
  | { type: "uncalibrated" }
  | { type: "none" };

/**
 * Ce que l'écran a le droit de montrer : un pourcentage seulement s'il est calibré, un intervalle
 * p10–p90 (signalé « non calibré » le cas échéant), sinon rien. Jamais de confiance inventée.
 */
export function confidenceView(c: Confidence): ConfidenceView {
  if (c.kind === "none") return { type: "none" };
  if (c.kind === "interval") {
    if (c.p10 === null || c.p90 === null) return { type: "none" };
    return { type: "interval", p10: c.p10, p90: c.p90, calibrated: c.calibrated };
  }
  if (!c.calibrated) return { type: "uncalibrated" };
  return c.value === null ? { type: "none" } : { type: "percent", value: c.value };
}

/** Seuil d'abstention de la vision (doc 16 §9.4 n° 8) : en dessous, « incertain, faites vérifier ». */
export const VISION_ABSTAIN_BELOW = 0.7;

export function showsAsPercent(probability: number | null, calibrated: boolean): boolean {
  return calibrated && probability !== null && probability >= 0 && probability <= 1;
}

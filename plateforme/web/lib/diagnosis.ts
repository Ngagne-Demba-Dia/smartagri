/**
 * Écran Maladies (service 8, doc 18 §10) : contrôle et réduction de la photo, lecture du verdict.
 * Calculs purs, sans accès au DOM : la partie navigateur est dans features/diagnosis/prepareImage.ts.
 */
import type { Diagnosis } from "@/lib/contracts/assistant";
import { VISION_ABSTAIN_BELOW } from "@/lib/contracts/provenance";

import type { Tone } from "./status";

const MEGABYTE = 1024 * 1024;

export const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"] as const;
/** Photo brute acceptée avant réduction (un téléphone en produit couramment 3 à 8 Mo). */
export const MAX_SOURCE_BYTES = 12 * MEGABYTE;
/** Plus grand côté de la photo envoyée ; assez pour une feuille, assez petit pour la limite du BFF. */
export const MAX_IMAGE_SIDE = 1024;
const MIN_IMAGE_SIDE = 320;
const SHRINK_FACTOR = 0.75;
export const JPEG_QUALITIES = [0.85, 0.7, 0.55, 0.4] as const;

export type ImageCheck = "ok" | "type" | "size" | "empty";

/** Contrôle d'un fichier avant toute lecture : format, taille, fichier vide. */
export function checkImageFile(file: { type: string; size: number }): ImageCheck {
  if (!(ACCEPTED_IMAGE_TYPES as readonly string[]).includes(file.type)) return "type";
  if (file.size === 0) return "empty";
  return file.size > MAX_SOURCE_BYTES ? "size" : "ok";
}

/** Dimensions réduites pour que le plus grand côté ne dépasse pas `maxSide` ; jamais d'agrandissement. */
export function fitWithin(width: number, height: number, maxSide: number): { width: number; height: number } {
  const longest = Math.max(width, height);
  if (longest <= maxSide) return { width, height };
  const ratio = maxSide / longest;
  return { width: Math.max(1, Math.round(width * ratio)), height: Math.max(1, Math.round(height * ratio)) };
}

export type Encoder = (maxSide: number, quality: number) => Promise<Blob>;

/**
 * Premier encodage qui tient dans `maxBytes`, en baissant d'abord la qualité puis la taille ;
 * null si même la plus petite version dépasse la limite.
 */
export async function encodeWithinLimit(
  encode: Encoder,
  maxBytes: number,
  startSide: number = MAX_IMAGE_SIDE,
): Promise<Blob | null> {
  for (let side = startSide; side >= MIN_IMAGE_SIDE; side = Math.floor(side * SHRINK_FACTOR)) {
    for (const quality of JPEG_QUALITIES) {
      const blob = await encode(side, quality);
      if (blob.size <= maxBytes) return blob;
    }
  }
  return null;
}

export type Verdict = "healthy" | "sick" | "suspect" | "uncertain";

export const VERDICT_TONE: Record<Verdict, Tone> = {
  healthy: "ok",
  sick: "bad",
  suspect: "warn",
  uncertain: "info",
};

/** Probabilité de la première hypothèse ; null si le service n'en donne aucune. */
export const topProbability = (d: Diagnosis): number | null => d.top3[0]?.probability ?? null;

/**
 * Verdict affiché. Sous le seuil d'abstention (0,7), ou sans hypothèse, ou si le service s'est abstenu :
 * « incertain, faites vérifier », même si l'étiquette reçue dit autrement.
 */
export function diagnosisVerdict(d: Diagnosis): Verdict {
  const best = topProbability(d);
  if (d.abstained || best === null || best < VISION_ABSTAIN_BELOW) return "uncertain";
  return d.label;
}

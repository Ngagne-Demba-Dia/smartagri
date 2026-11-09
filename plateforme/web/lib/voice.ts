/** Saisie vocale de l'assistant (service 17, doc 18 §10) : calculs purs, sans accès au micro. */
import { AUDIO_MAX_SECONDS, type Transcription } from "@/lib/contracts/assistant";

import type { AppLocale } from "./types";

const MS_PER_SECOND = 1000;
/** Formats d'enregistrement essayés dans l'ordre ; le navigateur retient le premier qu'il sait produire. */
export const AUDIO_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
] as const;

export const MAX_RECORDING_MS = AUDIO_MAX_SECONDS * MS_PER_SECOND;

/** Premier format accepté par le navigateur ; null si aucun (l'enregistrement est alors indisponible). */
export function pickAudioType(isSupported: (type: string) => boolean): string | null {
  return AUDIO_TYPES.find((type) => isSupported(type)) ?? null;
}

/** Durée envoyée au contrat : en secondes, au plus 60 s, jamais nulle. */
export function recordingSeconds(elapsedMs: number): number {
  const seconds = Math.min(elapsedMs, MAX_RECORDING_MS) / MS_PER_SECOND;
  return Math.max(seconds, 1 / MS_PER_SECOND);
}

export type VoiceOutcome = "text" | "empty";

/** Un texte vide (silence ou abstention) n'est jamais injecté dans le chat. */
export const transcriptionOutcome = (result: Transcription): VoiceOutcome =>
  result.text.trim() === "" ? "empty" : "text";

/** Ajoute la transcription au brouillon sans écraser ce qui est déjà saisi. L'envoi reste à l'utilisateur. */
export function appendTranscript(draft: string, text: string): string {
  const addition = text.trim();
  if (addition === "") return draft;
  return draft.trim() === "" ? addition : `${draft.trimEnd()} ${addition}`;
}

/** Langue indiquée au service : celle de l'interface (wo, ff, fr), qui est aussi celle du contrat. */
export const languageHint = (locale: AppLocale): AppLocale => locale;

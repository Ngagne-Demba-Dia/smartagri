import { describe, expect, it } from "vitest";

import { bytesToBase64 } from "@/lib/base64";
import type { Transcription } from "@/lib/contracts/assistant";
import {
  appendTranscript,
  AUDIO_TYPES,
  MAX_RECORDING_MS,
  pickAudioType,
  recordingSeconds,
  transcriptionOutcome,
} from "@/lib/voice";

const transcription = (text: string): Transcription =>
  ({ text, language: "fr", duration_s: 3, provenance: {} }) as unknown as Transcription;

describe("pickAudioType", () => {
  it("retient le premier format accepté, dans l'ordre de préférence", () => {
    expect(pickAudioType(() => true)).toBe(AUDIO_TYPES[0]);
    expect(pickAudioType((type) => type === "audio/mp4")).toBe("audio/mp4");
  });

  it("renvoie null si le navigateur n'en accepte aucun", () => {
    expect(pickAudioType(() => false)).toBeNull();
  });
});

describe("recordingSeconds", () => {
  it("convertit en secondes, plafonne à 60 s et reste strictement positif", () => {
    expect(recordingSeconds(2500)).toBe(2.5);
    expect(recordingSeconds(MAX_RECORDING_MS * 2)).toBe(60);
    expect(recordingSeconds(0)).toBeGreaterThan(0);
  });
});

describe("bytesToBase64", () => {
  it("encode de petits et de grands tampons", () => {
    expect(bytesToBase64(new Uint8Array([104, 105]))).toBe("aGk=");
    const big = new Uint8Array(100_000).fill(65);
    expect(atob(bytesToBase64(big))).toHaveLength(100_000);
  });
});

describe("transcriptionOutcome et appendTranscript", () => {
  it("un texte vide ou blanc n'est pas injecté", () => {
    expect(transcriptionOutcome(transcription(""))).toBe("empty");
    expect(transcriptionOutcome(transcription("  "))).toBe("empty");
    expect(transcriptionOutcome(transcription("Bonjour"))).toBe("text");
    expect(appendTranscript("déjà écrit", "  ")).toBe("déjà écrit");
  });

  it("ajoute au brouillon sans l'écraser", () => {
    expect(appendTranscript("", " Quand arroser ? ")).toBe("Quand arroser ?");
    expect(appendTranscript("Bonjour ", "quand arroser ?")).toBe("Bonjour quand arroser ?");
  });
});

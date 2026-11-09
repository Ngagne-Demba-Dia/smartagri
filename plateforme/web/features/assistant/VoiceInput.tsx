"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { ProvenanceNote } from "@/components/Provenance";
import { useErrorMessage } from "@/components/QueryState";
import { bytesToBase64 } from "@/lib/base64";
import type { Transcription } from "@/lib/contracts/assistant";
import type { AppLocale } from "@/lib/types";
import {
  languageHint,
  MAX_RECORDING_MS,
  pickAudioType,
  recordingSeconds,
  transcriptionOutcome,
} from "@/lib/voice";
import { useTranscribe } from "@/services/ai/assistant-transcribe";

type Phase = "idle" | "recording" | "sending";

const noopSubscribe = () => () => undefined;

/** Faux sur le serveur et pendant l'hydratation, vrai ensuite : évite un rendu différent des deux côtés. */
const useHydrated = (): boolean =>
  useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );

const supportsRecording = (): boolean =>
  typeof navigator !== "undefined" &&
  typeof MediaRecorder !== "undefined" &&
  Boolean(navigator.mediaDevices?.getUserMedia);

/**
 * Saisie vocale (service 17) : enregistre, envoie à la transcription et remet le texte à l'appelant,
 * qui le place dans le brouillon. Rien n'est envoyé au chat sans action de l'utilisateur.
 */
export function VoiceInput({ onText }: { onText: (text: string) => void }) {
  const t = useTranslations("assistant");
  const locale = useLocale() as AppLocale;
  const errorMessage = useErrorMessage();
  const transcribe = useTranscribe();
  const [phase, setPhase] = useState<Phase>("idle");
  const [micError, setMicError] = useState<string | null>(null);
  const [last, setLast] = useState<Transcription | null>(null);
  const hydrated = useHydrated();
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      recorder.current?.stream.getTracks().forEach((track) => track.stop());
    },
    [],
  );

  if (!hydrated) return null;
  if (!supportsRecording()) return <p className="text-xs text-mute">{t("voiceUnsupported")}</p>;

  const send = async (chunks: Blob[], type: string, startedAt: number) => {
    setPhase("sending");
    const buffer = await new Blob(chunks, { type }).arrayBuffer();
    transcribe.mutate(
      {
        audio_base64: bytesToBase64(new Uint8Array(buffer)),
        content_type: type.split(";")[0] ?? type,
        duration_s: recordingSeconds(Date.now() - startedAt),
        language_hint: languageHint(locale),
      },
      {
        onSuccess: (result) => {
          setLast(result);
          if (transcriptionOutcome(result) === "text") onText(result.text);
        },
        onSettled: () => setPhase("idle"),
      },
    );
  };

  const start = async () => {
    setMicError(null);
    setLast(null);
    transcribe.reset();
    const type = pickAudioType((candidate) => MediaRecorder.isTypeSupported(candidate));
    if (!type) {
      setMicError(t("voiceUnsupported"));
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: Blob[] = [];
      const startedAt = Date.now();
      const rec = new MediaRecorder(stream, { mimeType: type });
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        void send(chunks, type, startedAt);
      };
      recorder.current = rec;
      rec.start();
      setPhase("recording");
      timer.current = setTimeout(() => rec.state === "recording" && rec.stop(), MAX_RECORDING_MS);
    } catch {
      setMicError(t("voiceDenied"));
    }
  };

  const stop = () => {
    if (timer.current) clearTimeout(timer.current);
    if (recorder.current?.state === "recording") recorder.current.stop();
  };

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        className="btn-secondary self-start"
        onClick={phase === "recording" ? stop : () => void start()}
        disabled={phase === "sending"}
        aria-pressed={phase === "recording"}
      >
        {phase === "recording" ? t("voiceStop") : phase === "sending" ? t("voiceSending") : t("voiceStart")}
      </button>
      <p role="status" className="text-sm text-mute">
        {phase === "recording" ? t("voiceListening") : null}
        {last && transcriptionOutcome(last) === "empty" ? t("voiceNothing") : null}
      </p>
      {micError ? (
        <p role="alert" className="text-sm font-semibold text-bad-ink">
          {micError}
        </p>
      ) : null}
      {transcribe.isError ? (
        <p role="alert" className="text-sm font-semibold text-bad-ink">
          {errorMessage(transcribe.error)}
        </p>
      ) : null}
      {last && transcriptionOutcome(last) === "text" ? (
        <div className="text-sm">
          <p className="text-mute">{t("voiceCheck")}</p>
          <ProvenanceNote provenance={last.provenance} />
        </div>
      ) : null}
    </div>
  );
}

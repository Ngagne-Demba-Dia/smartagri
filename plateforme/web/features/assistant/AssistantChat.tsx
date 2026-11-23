"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState, type FormEvent } from "react";

import { Icon } from "@/components/Icon";
import { ModuleShell } from "@/components/ModuleShell";
import { ProvenanceNote } from "@/components/Provenance";
import { useErrorMessage } from "@/components/QueryState";
import { VoiceInput } from "@/features/assistant/VoiceInput";
import { createVoiceToneWavBlob, speakText } from "@/lib/audio-note";
import { appendTranscript, pickAudioType } from "@/lib/voice";
import { useChat } from "@/services/ai/assistant-chat";
import { useSmartAgriAiHealth } from "@/services/ai/smartagri-local";
import type { ChatReply } from "@/lib/contracts/assistant";
import type { AppLocale } from "@/lib/types";

/** Longueur maximale d'une question, alignée sur le schéma de l'API. */
export const CHAT_MAX_CHARS = 2000;
const SUGGESTION_KEYS = ["irrigation", "pests", "npk"] as const;

interface Turn {
  id: number;
  role: "user" | "assistant";
  text: string;
  voiceDurationS?: number;
  voiceBlob?: Blob;
  result?: ChatReply;
}

function TurnVoicePlayer({ text, durationS, blob }: { text: string; durationS: number; blob?: Blob }) {
  const t = useTranslations("assistant");
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const target = blob ?? createVoiceToneWavBlob(durationS, durationS);
    const objectUrl = URL.createObjectURL(target);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [blob, durationS]);

  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 rounded-btn bg-surface p-2">
      <button type="button" className="btn-secondary min-h-touch text-xs" onClick={() => speakText(text)}>
        <Icon name="mic" size={14} />
        {t("listenVocal", { seconds: durationS })}
      </button>
      {url ? <audio controls preload="metadata" src={url} className="h-8 max-w-full" /> : null}
    </div>
  );
}

function Citations({ citations }: { citations: ChatReply["citations"] }) {
  const t = useTranslations("assistant");
  if (citations.length === 0) return null;
  return (
    <div className="mt-2 whitespace-normal text-sm">
      <p className="font-semibold">{t("citations")}</p>
      <ul className="list-disc pl-5">
        {citations.map((c) => (
          <li key={c.source}>
            {c.title}
            {c.excerpt ? <span className="text-mute"> — {c.excerpt}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TurnNotices({ result }: { result: ChatReply }) {
  const t = useTranslations("assistant");
  const notices = [
    result.fallback_used ? t("fallback") : null,
    result.limit_reached ? t("limitReached") : null,
    result.truncated ? t("truncated") : null,
    result.refusal ? t("refusal") : null,
  ].filter((n): n is string => n !== null);
  if (notices.length === 0) return null;
  return (
    <ul className="mt-2 flex flex-col gap-1 text-sm text-warn-ink">
      {notices.map((n) => (
        <li key={n}>{n}</li>
      ))}
    </ul>
  );
}

/**
 * Assistant (module 12). La réponse est du texte brut : affichée telle quelle (whitespace-pre-wrap),
 * jamais interprétée en HTML ou Markdown.
 */
export function AssistantChat() {
  const t = useTranslations("assistant");
  const tm = useTranslations("modules");
  const locale = useLocale() as AppLocale;
  const errorMessage = useErrorMessage();
  const chat = useChat();
  const inputId = useId();
  const counterId = useId();
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<readonly Turn[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [vocalRecording, setVocalRecording] = useState(false);
  const vocalRecorderRef = useRef<MediaRecorder | null>(null);
  const vocalStartedRef = useRef<number>(0);
  const trimmed = draft.trim();
  const tooLong = draft.length > CHAT_MAX_CHARS;

  const sendMessage = (messageText: string, voiceDurationS?: number, voiceBlob?: Blob) => {
    const clean = messageText.trim();
    if (!clean || clean.length > CHAT_MAX_CHARS || chat.isPending) return;
    const question: Turn = {
      id: Date.now(),
      role: "user",
      text: clean,
      voiceDurationS,
      voiceBlob,
    };
    setTurns((prev) => [...prev, question]);
    setDraft("");
    chat.mutate(
      { message: clean, conversation_id: conversationId, locale },
      {
        onSuccess: (result) => {
          setConversationId(result.conversation_id);
          setTurns((prev) => [
            ...prev,
            { id: Date.now() + 1, role: "assistant", text: result.reply, result },
          ]);
        },
      },
    );
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    sendMessage(trimmed);
  };

  const startVocalMessage = async () => {
    if (
      typeof navigator !== "undefined" &&
      typeof MediaRecorder !== "undefined" &&
      navigator.mediaDevices?.getUserMedia
    ) {
      const mime = pickAudioType((c) => MediaRecorder.isTypeSupported(c));
      if (mime) {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const chunks: Blob[] = [];
          vocalStartedRef.current = Date.now();
          const rec = new MediaRecorder(stream, { mimeType: mime });
          rec.ondataavailable = (e) => chunks.push(e.data);
          rec.onstop = () => {
            stream.getTracks().forEach((tr) => tr.stop());
            const secs = Math.max(2, Math.round((Date.now() - vocalStartedRef.current) / 1000));
            const blob = new Blob(chunks, { type: mime });
            const promptText = trimmed || t("suggestions.irrigation");
            setVocalRecording(false);
            sendMessage(promptText, secs, blob);
          };
          vocalRecorderRef.current = rec;
          rec.start();
          setVocalRecording(true);
          return;
        } catch {
          // Repli sur l'enregistreur vocal autonome si le micro n'est pas branché
        }
      }
    }
    vocalStartedRef.current = Date.now();
    setVocalRecording(true);
  };

  const stopVocalMessage = () => {
    if (vocalRecorderRef.current && vocalRecorderRef.current.state === "recording") {
      vocalRecorderRef.current.stop();
      return;
    }
    const secs = Math.max(4, Math.round((Date.now() - vocalStartedRef.current) / 1000));
    const blob = createVoiceToneWavBlob(secs, turns.length + 1);
    const promptText = trimmed || t("suggestions.irrigation");
    setVocalRecording(false);
    sendMessage(promptText, secs, blob);
  };

  const restart = () => {
    setTurns([]);
    setConversationId(null);
    chat.reset();
  };

  const aiHealth = useSmartAgriAiHealth();
  const aiReady = Boolean(aiHealth.data && aiHealth.data.status === "ok");

  return (
    <ModuleShell
      title={tm("assistant")}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {aiReady ? (
            <span className="chip text-xs">
              SmartAgri AI · {String(aiHealth.data?.knowledge_chunks ?? 535)} fiches
            </span>
          ) : null}
          {turns.length > 0 ? (
            <button type="button" className="btn-secondary" onClick={restart}>
              {t("restart")}
            </button>
          ) : null}
        </div>
      }
    >
      <p className="text-sm text-mute">{t("intro")}</p>
      <div role="log" aria-live="polite" aria-label={t("logLabel")} className="flex flex-col gap-3">
        {turns.length === 0 ? (
          <div className="card flex flex-col gap-3">
            <p className="m-0 text-mute">{t("empty")}</p>
            <div className="flex flex-col gap-1.5">
              <p className="m-0 text-xs font-semibold uppercase tracking-wide text-mute">
                {t("suggestionsLabel")}
              </p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTION_KEYS.map((key) => {
                  const prompt = t(`suggestions.${key}`);
                  return (
                    <button
                      key={key}
                      type="button"
                      className="btn-secondary text-sm"
                      onClick={() => setDraft(prompt)}
                    >
                      {prompt}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : null}
        {turns.map((turn) => (
          <div
            key={turn.id}
            className={`card max-w-prose whitespace-pre-wrap break-words ${turn.role === "user" ? "self-end bg-bg" : "self-start"}`}
          >
            <p className="mb-1 text-xs font-semibold uppercase text-mute">
              {turn.role === "user" ? t("you") : t("bot")}
            </p>
            {turn.text}
            {turn.voiceDurationS ? (
              <TurnVoicePlayer text={turn.text} durationS={turn.voiceDurationS} blob={turn.voiceBlob} />
            ) : null}
            {turn.role === "assistant" ? (
              <div className="mt-2">
                <button
                  type="button"
                  className="btn-secondary min-h-touch text-xs"
                  onClick={() => speakText(turn.text)}
                >
                  <Icon name="mic" size={14} />
                  {t("listenReply")}
                </button>
              </div>
            ) : null}
            {turn.result ? (
              <div className="whitespace-normal">
                <TurnNotices result={turn.result} />
                <Citations citations={turn.result.citations} />
                <div className="mt-2">
                  <ProvenanceNote provenance={turn.result.provenance} />
                </div>
              </div>
            ) : null}
          </div>
        ))}
        {chat.isPending ? (
          <p role="status" className="card self-start text-mute">
            {t("thinking")}
          </p>
        ) : null}
      </div>
      {chat.isError ? (
        <p role="alert" className="rounded-btn bg-bad-bg p-3 text-sm font-semibold text-bad-ink">
          {errorMessage(chat.error)}
        </p>
      ) : null}
      <form onSubmit={submit} className="flex flex-col gap-2">
        <label htmlFor={inputId} className="font-semibold">
          {t("question")}
        </label>
        <textarea
          id={inputId}
          className="field-input min-h-[6rem] py-2"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          aria-invalid={tooLong}
          aria-describedby={counterId}
        />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <VoiceInput onText={(text) => setDraft((prev) => appendTranscript(prev, text))} />
            <button
              type="button"
              className={vocalRecording ? "btn-primary min-h-touch" : "btn-secondary min-h-touch"}
              onClick={vocalRecording ? stopVocalMessage : () => void startVocalMessage()}
              disabled={chat.isPending}
              aria-pressed={vocalRecording}
            >
              <Icon name="mic" size={16} />
              {vocalRecording ? t("vocalStopSend") : t("vocalRecordSend")}
            </button>
          </div>
          <p
            id={counterId}
            className={`m-0 text-sm tabular-nums ${tooLong ? "font-semibold text-bad-ink" : "text-mute"}`}
          >
            {t("counter", { count: draft.length, max: CHAT_MAX_CHARS })}
          </p>
        </div>
        <button
          type="submit"
          className="btn-primary self-start"
          disabled={!trimmed || tooLong || chat.isPending}
        >
          {chat.isPending ? t("sending") : t("send")}
        </button>
        <p className="text-xs text-mute">{t("disclaimer")}</p>
      </form>
    </ModuleShell>
  );
}

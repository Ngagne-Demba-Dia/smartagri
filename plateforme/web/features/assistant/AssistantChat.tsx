"use client";

import { useLocale, useTranslations } from "next-intl";
import { useId, useState, type FormEvent } from "react";

import { ModuleShell } from "@/components/ModuleShell";
import { ProvenanceNote } from "@/components/Provenance";
import { useErrorMessage } from "@/components/QueryState";
import { VoiceInput } from "@/features/assistant/VoiceInput";
import { appendTranscript } from "@/lib/voice";
import { useChat } from "@/services/ai/assistant-chat";
import type { ChatReply } from "@/lib/contracts/assistant";
import type { AppLocale } from "@/lib/types";

/** Longueur maximale d'une question, alignée sur le schéma de l'API. */
export const CHAT_MAX_CHARS = 2000;
const SUGGESTION_KEYS = ["irrigation", "pests", "npk"] as const;

interface Turn {
  id: number;
  role: "user" | "assistant";
  text: string;
  result?: ChatReply;
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
  const trimmed = draft.trim();
  const tooLong = draft.length > CHAT_MAX_CHARS;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!trimmed || tooLong || chat.isPending) return;
    const question: Turn = { id: Date.now(), role: "user", text: trimmed };
    setTurns((prev) => [...prev, question]);
    setDraft("");
    chat.mutate(
      { message: trimmed, conversation_id: conversationId, locale },
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

  const restart = () => {
    setTurns([]);
    setConversationId(null);
    chat.reset();
  };

  return (
    <ModuleShell
      title={tm("assistant")}
      actions={
        turns.length > 0 ? (
          <button type="button" className="btn-secondary" onClick={restart}>
            {t("restart")}
          </button>
        ) : null
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
          <VoiceInput onText={(text) => setDraft((prev) => appendTranscript(prev, text))} />
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

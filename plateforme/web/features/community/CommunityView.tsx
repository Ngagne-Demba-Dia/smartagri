"use client";

import { useTranslations } from "next-intl";
import { useEffect, useId, useMemo, useRef, useState, type FormEvent } from "react";

import { Icon } from "@/components/Icon";
import { KpiCard } from "@/components/KpiCard";
import { ModuleShell } from "@/components/ModuleShell";
import { Segmented } from "@/components/Segmented";
import { StatusTag } from "@/components/StatusTag";
import { createVoiceToneWavBlob, speakText } from "@/lib/audio-note";
import { formatNumber } from "@/lib/format";
import type { Tone } from "@/lib/status";
import { pickAudioType } from "@/lib/voice";

export type CommunityCategory = "disease" | "insects" | "birds" | "advice";
type FilterCategory = "all" | CommunityCategory;

export interface CommunityReply {
  id: string;
  author: string;
  zone: string;
  text: string;
  voiceDurationS: number | null;
  createdAt: string;
}

export interface CommunityPost {
  id: string;
  category: CommunityCategory;
  author: string;
  roleLabel: string;
  zone: string;
  crop: string;
  title: string;
  text: string;
  voiceDurationS: number | null;
  voiceBlob?: Blob;
  createdAt: string;
  confirmations: number;
  confirmedByMe?: boolean;
  replies: readonly CommunityReply[];
}

const CATEGORY_TONE: Record<CommunityCategory, Tone> = {
  disease: "bad",
  insects: "warn",
  birds: "warn",
  advice: "ok",
};

const ZONES = ["Mboro (Niayes)", "Potou (Niayes)", "Ndiol (Vallée du Fleuve)"] as const;

export const INITIAL_COMMUNITY_POSTS: readonly CommunityPost[] = [
  {
    id: "post-birds-1",
    category: "birds",
    author: "Mamadou Diop",
    roleLabel: "Producteur · Ndiol",
    zone: "Ndiol (Vallée du Fleuve)",
    crop: "Riz & Oignon",
    title: "Passage de bandes d’oiseaux granivores (mange-mil) secteur Ndiol Nord",
    text: "Attention aux parcelles proches du canal : gros vols d’oiseaux observés tôt ce matin entre 6 h 30 et 8 h 30. Renforcez le gardiennage et les rubans effaroucheurs.",
    voiceDurationS: 7,
    createdAt: "Il y a 25 min",
    confirmations: 8,
    replies: [
      {
        id: "rep-1",
        author: "Ousmane Sow",
        zone: "Ndiol (Vallée du Fleuve)",
        text: "Confirmé aussi côté Ross-Béthio, nous avons installé les filets et mobilisé l’équipe de surveillance.",
        voiceDurationS: 5,
        createdAt: "Il y a 12 min",
      },
    ],
  },
  {
    id: "post-insects-1",
    category: "insects",
    author: "Fatou Ndiaye",
    roleLabel: "Productrice · Mboro",
    zone: "Mboro (Niayes)",
    crop: "Oignon Violet de Galmi",
    title: "Campagne d’insectes : hausse des captures de thrips et noctuelles",
    text: "Mes plaques engluées jaunes ont capturé plus de 18 thrips en 48 h sur Mboro 1. Vérifiez le cœur des feuilles d’oignon avant la montée des températures.",
    voiceDurationS: 9,
    createdAt: "Il y a 1 h",
    confirmations: 11,
    replies: [
      {
        id: "rep-2",
        author: "Cheikh Ba (Agronome)",
        zone: "Mboro (Niayes)",
        text: "Bon réflexe. Privilégiez un arrosage matinal et évitez les excès d’azote qui attirent les thrips.",
        voiceDurationS: null,
        createdAt: "Il y a 40 min",
      },
    ],
  },
  {
    id: "post-disease-1",
    category: "disease",
    author: "Ibrahima Sarr",
    roleLabel: "Producteur · Potou",
    zone: "Potou (Niayes)",
    crop: "Tomate & Pomme de terre",
    title: "Alerte maladie : taches de mildiou après la rosée nocturne",
    text: "Après 3 nuits très humides (> 85 % HR), premières taches brunes observées sur les feuilles basses de tomate. Évitez d’arroser par aspersion le soir.",
    voiceDurationS: 6,
    createdAt: "Il y a 3 h",
    confirmations: 6,
    replies: [],
  },
  {
    id: "post-advice-1",
    category: "advice",
    author: "Awa Fall",
    roleLabel: "Coopérative des Niayes",
    zone: "Mboro (Niayes)",
    crop: "Maraîchage goutte-à-goutte",
    title: "Conseil irrigation & pH de l’eau : nettoyage des filtres et goutteurs",
    text: "Sur les forages où le pH dépasse 7,4 (eau calcaire), pensez à rincer les rampes goutte-à-goutte chaque quinzaine pour garder un débit régulier.",
    voiceDurationS: 8,
    createdAt: "Aujourd’hui",
    confirmations: 14,
    replies: [],
  },
];

/** Lecteur de note vocale compatible CSP (`blob:` + synthèse vocale pour écouter le message). */
function VoiceNotePlayer({
  text,
  durationS,
  blob,
  seed,
}: {
  text: string;
  durationS: number;
  blob?: Blob;
  seed: number;
}) {
  const t = useTranslations("community");
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    const target = blob ?? createVoiceToneWavBlob(durationS, seed);
    const objectUrl = URL.createObjectURL(target);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [blob, durationS, seed]);

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-btn bg-surface p-2">
      <button
        type="button"
        className="btn-secondary min-h-touch text-sm"
        onClick={() => speakText(text)}
      >
        <Icon name="mic" size={16} />
        {t("listenVoice", { seconds: durationS })}
      </button>
      {url ? (
        <audio
          controls
          preload="metadata"
          src={url}
          aria-label={t("voicePlayerLabel", { seconds: durationS })}
          className="h-9 max-w-full"
        />
      ) : null}
    </div>
  );
}

/** Communauté entre agriculteurs : alertes maladies, campagnes d'insectes, campagnes d'oiseaux, conseils écrits et vocaux. */
export function CommunityView() {
  const t = useTranslations("community");
  const tm = useTranslations("modules");
  const titleId = useId();
  const textId = useId();
  const zoneId = useId();
  const cropId = useId();

  const [posts, setPosts] = useState<readonly CommunityPost[]>(INITIAL_COMMUNITY_POSTS);
  const [filter, setFilter] = useState<FilterCategory>("all");
  const [category, setCategory] = useState<CommunityCategory>("disease");
  const [zone, setZone] = useState<string>(ZONES[0]);
  const [crop, setCrop] = useState("Oignon Violet de Galmi");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedSeconds, setRecordedSeconds] = useState<number | null>(null);
  const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});

  const recorderRef = useRef<MediaRecorder | null>(null);
  const startedAtRef = useRef<number>(0);

  const shown = useMemo(
    () => (filter === "all" ? posts : posts.filter((p) => p.category === filter)),
    [posts, filter],
  );

  const counts = useMemo(
    () => ({
      total: posts.length,
      diseases: posts.filter((p) => p.category === "disease").length,
      insects: posts.filter((p) => p.category === "insects").length,
      birds: posts.filter((p) => p.category === "birds").length,
    }),
    [posts],
  );

  const startVoiceRecording = async () => {
    setRecordedBlob(null);
    setRecordedSeconds(null);
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
          startedAtRef.current = Date.now();
          const rec = new MediaRecorder(stream, { mimeType: mime });
          rec.ondataavailable = (e) => chunks.push(e.data);
          rec.onstop = () => {
            stream.getTracks().forEach((tr) => tr.stop());
            const secs = Math.max(2, Math.round((Date.now() - startedAtRef.current) / 1000));
            setRecordedBlob(new Blob(chunks, { type: mime }));
            setRecordedSeconds(secs);
            setRecording(false);
          };
          recorderRef.current = rec;
          rec.start();
          setRecording(true);
          return;
        } catch {
          // Si le micro physique est absent ou refusé, on bascule sur l'enregistreur vocal simulé.
        }
      }
    }
    // Mode sans micro physique : démarre le compteur et génère la note vocale à l'arrêt.
    startedAtRef.current = Date.now();
    setRecording(true);
  };

  const stopVoiceRecording = () => {
    if (recorderRef.current && recorderRef.current.state === "recording") {
      recorderRef.current.stop();
      return;
    }
    const secs = Math.max(4, Math.round((Date.now() - startedAtRef.current) / 1000));
    setRecordedBlob(createVoiceToneWavBlob(secs, posts.length + 1));
    setRecordedSeconds(secs);
    setRecording(false);
    if (!text.trim()) {
      setText(t(`voiceTemplates.${category}`));
    }
    if (!title.trim()) {
      setTitle(t(`voiceTitles.${category}`));
    }
  };

  const submitPost = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const finalTitle = title.trim() || t(`voiceTitles.${category}`);
    const finalText = text.trim() || (recordedSeconds ? t(`voiceTemplates.${category}`) : "");
    if (!finalText && !recordedSeconds) return;

    const newPost: CommunityPost = {
      id: `post-${Date.now()}`,
      category,
      author: t("youAuthor"),
      roleLabel: t("youRole"),
      zone,
      crop: crop.trim() || "Maraîchage",
      title: finalTitle,
      text: finalText,
      voiceDurationS: recordedSeconds,
      voiceBlob: recordedBlob ?? undefined,
      createdAt: t("justNow"),
      confirmations: 1,
      confirmedByMe: true,
      replies: [],
    };
    setPosts((prev) => [newPost, ...prev]);
    setTitle("");
    setText("");
    setRecordedBlob(null);
    setRecordedSeconds(null);
  };

  const toggleConfirm = (postId: string) => {
    setPosts((prev) =>
      prev.map((p) =>
        p.id === postId
          ? {
              ...p,
              confirmations: p.confirmedByMe ? p.confirmations - 1 : p.confirmations + 1,
              confirmedByMe: !p.confirmedByMe,
            }
          : p,
      ),
    );
  };

  const addReply = (postId: string, withVoice: boolean) => {
    const raw = (replyDrafts[postId] ?? "").trim();
    const replyText = raw || (withVoice ? t("voiceReplyDefault") : "");
    if (!replyText) return;
    const reply: CommunityReply = {
      id: `rep-${Date.now()}`,
      author: t("youAuthor"),
      zone,
      text: replyText,
      voiceDurationS: withVoice ? 5 : null,
      createdAt: t("justNow"),
    };
    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, replies: [...p.replies, reply] } : p)),
    );
    setReplyDrafts((prev) => ({ ...prev, [postId]: "" }));
  };

  return (
    <ModuleShell title={tm("community")} description={t("description")} version="MVP">
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label={t("kpiTotal")} value={formatNumber(counts.total, 0)} icon="chat" />
        <KpiCard label={t("kpiDiseases")} value={formatNumber(counts.diseases, 0)} icon="camera" />
        <KpiCard label={t("kpiInsects")} value={formatNumber(counts.insects, 0)} icon="bug" />
        <KpiCard label={t("kpiBirds")} value={formatNumber(counts.birds, 0)} icon="bell" />
      </dl>

      <form onSubmit={submitPost} className="card flex flex-col gap-4" aria-label={t("formTitle")}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 flex items-center gap-2 text-lg font-bold text-ink">
            <Icon name="chat" size={20} />
            {t("formTitle")}
          </h2>
          <StatusTag tone={CATEGORY_TONE[category]} label={t(`categories.${category}`)} />
        </div>

        <Segmented
          legend={t("categoryLegend")}
          value={category}
          onChange={setCategory}
          options={[
            { value: "disease", label: t("categories.disease") },
            { value: "insects", label: t("categories.insects") },
            { value: "birds", label: t("categories.birds") },
            { value: "advice", label: t("categories.advice") },
          ]}
        />

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label htmlFor={zoneId} className="text-sm font-semibold">
              {t("zoneLabel")}
            </label>
            <select
              id={zoneId}
              className="field-input min-h-touch"
              value={zone}
              onChange={(e) => setZone(e.target.value)}
            >
              {ZONES.map((z) => (
                <option key={z} value={z}>
                  {z}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor={cropId} className="text-sm font-semibold">
              {t("cropLabel")}
            </label>
            <input
              id={cropId}
              className="field-input min-h-touch"
              value={crop}
              onChange={(e) => setCrop(e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor={titleId} className="text-sm font-semibold">
            {t("titleLabel")}
          </label>
          <input
            id={titleId}
            className="field-input min-h-touch"
            placeholder={t(`voiceTitles.${category}`)}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor={textId} className="text-sm font-semibold">
            {t("messageLabel")}
          </label>
          <textarea
            id={textId}
            className="field-input min-h-[5rem] py-2"
            placeholder={t("messagePlaceholder")}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded-btn bg-surface p-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={recording ? "btn-primary min-h-touch" : "btn-secondary min-h-touch"}
              onClick={recording ? stopVoiceRecording : () => void startVoiceRecording()}
              aria-pressed={recording}
            >
              <Icon name="mic" size={16} />
              {recording ? t("stopVocal") : t("recordVocal")}
            </button>
            {recording ? (
              <span role="status" className="text-sm font-semibold text-warn-ink">
                {t("recordingNow")}
              </span>
            ) : null}
            {recordedSeconds !== null ? (
              <StatusTag tone="ok" label={t("vocalReady", { seconds: recordedSeconds })} />
            ) : null}
          </div>
          <button
            type="submit"
            className="btn-primary min-h-touch"
            disabled={!text.trim() && recordedSeconds === null}
          >
            <Icon name="send" size={16} />
            {t("publish")}
          </button>
        </div>

        {recordedSeconds !== null ? (
          <VoiceNotePlayer
            text={text.trim() || t(`voiceTemplates.${category}`)}
            durationS={recordedSeconds}
            blob={recordedBlob ?? undefined}
            seed={99}
          />
        ) : null}
      </form>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Segmented
          legend={t("filterLegend")}
          value={filter}
          onChange={setFilter}
          options={[
            { value: "all", label: t("filterAll") },
            { value: "disease", label: t("categories.disease") },
            { value: "insects", label: t("categories.insects") },
            { value: "birds", label: t("categories.birds") },
            { value: "advice", label: t("categories.advice") },
          ]}
        />
      </div>

      <ul aria-label={t("feedLabel")} className="m-0 flex list-none flex-col gap-4 p-0">
        {shown.map((post, idx) => (
          <li key={post.id} className="card flex flex-col gap-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="flex flex-col gap-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusTag tone={CATEGORY_TONE[post.category]} label={t(`categories.${post.category}`)} />
                  <span className="chip">
                    <Icon name="map" size={14} />
                    {post.zone}
                  </span>
                  <span className="chip">
                    <Icon name="leaf" size={14} />
                    {post.crop}
                  </span>
                </div>
                <h3 className="m-0 mt-1 text-lg font-bold text-ink">{post.title}</h3>
              </div>
              <span className="text-xs text-mute">
                {post.author} ({post.roleLabel}) · {post.createdAt}
              </span>
            </div>

            <p className="m-0 text-base text-ink">{post.text}</p>

            {post.voiceDurationS !== null ? (
              <VoiceNotePlayer
                text={post.text}
                durationS={post.voiceDurationS}
                blob={post.voiceBlob}
                seed={idx + 1}
              />
            ) : null}

            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line pt-2">
              <button
                type="button"
                className="btn-secondary min-h-touch text-sm"
                onClick={() => toggleConfirm(post.id)}
                aria-pressed={Boolean(post.confirmedByMe)}
              >
                <Icon name="check" size={16} />
                {t("confirmBtn", { count: post.confirmations })}
              </button>
              <span className="text-xs text-mute">
                {t("repliesCount", { count: post.replies.length })}
              </span>
            </div>

            {post.replies.length > 0 ? (
              <ul className="m-0 flex list-none flex-col gap-2 pl-4">
                {post.replies.map((rep, rIdx) => (
                  <li key={rep.id} className="rounded-btn bg-surface p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold">{rep.author}</span>
                      <span className="text-xs text-mute">
                        {rep.zone} · {rep.createdAt}
                      </span>
                    </div>
                    <p className="m-0 mt-1">{rep.text}</p>
                    {rep.voiceDurationS !== null ? (
                      <div className="mt-2">
                        <VoiceNotePlayer text={rep.text} durationS={rep.voiceDurationS} seed={rIdx + 20} />
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : null}

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                aria-label={t("replyPlaceholder")}
                placeholder={t("replyPlaceholder")}
                className="field-input min-h-touch flex-1 text-sm"
                value={replyDrafts[post.id] ?? ""}
                onChange={(e) => setReplyDrafts((prev) => ({ ...prev, [post.id]: e.target.value }))}
              />
              <button
                type="button"
                className="btn-secondary min-h-touch text-sm"
                onClick={() => addReply(post.id, false)}
              >
                <Icon name="send" size={14} />
                {t("replySend")}
              </button>
              <button
                type="button"
                className="btn-secondary min-h-touch text-sm"
                onClick={() => addReply(post.id, true)}
              >
                <Icon name="mic" size={14} />
                {t("replyVoice")}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </ModuleShell>
  );
}

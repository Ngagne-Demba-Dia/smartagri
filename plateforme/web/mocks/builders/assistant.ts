/**
 * Réponses simulées de l'assistant et de la vision (doc 16 §9, services 8, 16 et 17). Textes de
 * démonstration en français, citations fictives « demo:// » : aucune donnée réelle, aucun appel externe.
 */
import type { ChatReply, ChatRequest, Diagnosis, DiagnosisInput, TranscribeInput, Transcription } from "@/lib/contracts/assistant";

import { round } from "../base";
import { between, hash32 } from "../fixtures/series";
import { NO_CONFIDENCE, classProbability, probability, provenance } from "../provenance";
import type { MockScenario } from "../scenario";

/* ---------- 8. disease_diagnosis ---------- */

const DISEASES = ["downy_mildew", "alternaria_leaf_spot", "fusarium_wilt"] as const;
const SICK_TOP3 = [0.86, 0.08, 0.04] as const;
const HEALTHY_TOP3 = [0.91, 0.05, 0.02] as const;
const ABSTAIN_TOP3 = [0.41, 0.33, 0.18] as const;
const IMAGE_KEY_CHARS = 96;

const imageKey = (input: DiagnosisInput): number => hash32(input.image_base64.slice(0, IMAGE_KEY_CHARS));

function rotate<T>(items: readonly T[], start: number): T[] {
  return items.map((_, i) => items[(start + i) % items.length] as T);
}

/** Analyse d'une photo ; `id` non null quand la route enregistre le diagnostic (POST /v1/diagnoses). */
export function diagnosis(input: DiagnosisInput, id: string | null, scenario: MockScenario, now: Date): Diagnosis {
  const key = imageKey(input);
  const codes = rotate(DISEASES, key % DISEASES.length);
  const base = { id, captured_at: input.captured_at };
  if (scenario === "empty") {
    return {
      ...base,
      label: "suspect",
      disease_code: null,
      top3: [],
      abstained: true,
      provenance: provenance("disease_diagnosis", scenario, now, { confidence: NO_CONFIDENCE }),
    };
  }
  if (scenario === "abstention") {
    return {
      ...base,
      label: "suspect",
      disease_code: null,
      top3: codes.map((code, i) => ({ code, probability: ABSTAIN_TOP3[i] ?? 0 })),
      abstained: true,
      provenance: provenance("disease_diagnosis", scenario, now, {
        confidence: classProbability(ABSTAIN_TOP3[0], true),
        keepConfidence: true,
      }),
    };
  }
  const healthy = key % 4 === 0;
  const top3 = healthy
    ? ["healthy", ...codes.slice(0, 2)].map((code, i) => ({ code, probability: HEALTHY_TOP3[i] ?? 0 }))
    : codes.map((code, i) => ({ code, probability: SICK_TOP3[i] ?? 0 }));
  const best = top3[0]?.probability ?? null;
  return {
    ...base,
    label: healthy ? "healthy" : "sick",
    disease_code: healthy ? null : (codes[0] ?? null),
    top3,
    abstained: false,
    provenance: provenance("disease_diagnosis", scenario, now, {
      confidence: classProbability(best, true),
      keepConfidence: true,
    }),
  };
}

/* ---------- 16. assistant_chat ---------- */

type Topic = "irrigation" | "fertilisation" | "disease" | "price" | "general";

const TOPIC_KEYWORDS: readonly { topic: Topic; words: readonly string[] }[] = [
  { topic: "irrigation", words: ["arros", "irrig", "eau", "pomp"] },
  { topic: "fertilisation", words: ["engrais", "npk", "azote", "fertil"] },
  { topic: "disease", words: ["maladie", "mildiou", "feuille", "tache", "ravageur", "insecte"] },
  { topic: "price", words: ["prix", "marché", "marche", "vendre"] },
];

interface TopicAnswer {
  reply: string;
  citations: ChatReply["citations"];
}

const cite = (n: number, title: string, excerpt: string) => ({
  title: `Fiche de démonstration n° ${n} — ${title}`,
  source: `demo://fiches/${n}`,
  excerpt,
});

const ANSWERS: Readonly<Record<Topic, TopicAnswer>> = {
  irrigation: {
    reply:
      "Arrosez tôt le matin ou en fin de journée pour limiter l'évaporation. Sur sol sableux (dior), " +
      "préférez des apports courts et fréquents. Le besoin calculé pour chaque parcelle est affiché dans " +
      "l'onglet Recommandations, avec sa provenance et sa date de calcul.",
    citations: [cite(3, "Irrigation goutte-à-goutte en zone des Niayes", "Apports fractionnés sur sols à faible réserve utile.")],
  },
  fertilisation: {
    reply:
      "Les valeurs NPK du kit sont indicatives tant que la sonde n'est pas étalonnée. Avant tout apport, " +
      "faites confirmer par une analyse de sol ; la dose conseillée par culture figure dans la fiche de la parcelle.",
    citations: [cite(7, "Fertilisation des cultures maraîchères", "Fractionner l'azote selon le stade de la culture.")],
  },
  disease: {
    reply:
      "Prenez une photo nette de la feuille atteinte, en lumière naturelle, et lancez une analyse. Si le " +
      "résultat est incertain, faites vérifier par un conseiller agricole avant tout traitement.",
    citations: [
      cite(12, "Reconnaître le mildiou de l'oignon", "Taches allongées vert pâle, duvet violacé par temps humide."),
      cite(14, "Lutte intégrée contre les ravageurs", "Surveiller les pièges avant de traiter."),
    ],
  },
  price: {
    reply:
      "La prévision de prix donne une fourchette (p10–p90) sur quatre semaines, en FCFA par kilo. " +
      "C'est une tendance indicative : vérifiez le prix du jour auprès de votre marché avant de vendre.",
    citations: [cite(21, "Lire une prévision de prix", "Une fourchette large signale une forte incertitude.")],
  },
  general: {
    reply:
      "Je peux vous aider sur l'irrigation, la fertilisation, les maladies et ravageurs, ou les prix. " +
      "Posez votre question en précisant la parcelle et la culture concernées.",
    citations: [cite(1, "Prise en main de la plateforme", "Chaque résultat affiche sa source et sa fraîcheur.")],
  },
};

const LANGUAGE_NOTE =
  "Réponse en français : le wolof et le pulaar ne sont pas encore disponibles dans cette démonstration.";
const FALLBACK_NOTE = "Mode dégradé : réponse tirée des fiches, sans modèle de langage.";
const NO_SOURCE_REPLY = "Je n'ai trouvé aucune source dans les fiches pour répondre à cette question.";
const REFUSAL_REPLY = "Je préfère ne pas répondre : les sources disponibles ne suffisent pas pour un conseil fiable.";
const MOCK_MODEL = "mock-asst-llm-1";

export function topicOf(message: string): Topic {
  const lower = message.toLowerCase();
  return TOPIC_KEYWORDS.find((t) => t.words.some((w) => lower.includes(w)))?.topic ?? "general";
}

export function chatReply(input: ChatRequest, scenario: MockScenario, now: Date): ChatReply {
  const conversationId = input.conversation_id ?? `conv-mock-${hash32(input.message).toString(36)}`;
  const answer = ANSWERS[topicOf(input.message)];
  const fallback = scenario === "fallback";
  const note = input.locale === "wo" || input.locale === "ff" ? `${LANGUAGE_NOTE}\n\n` : "";
  const base = {
    conversation_id: conversationId,
    stop_reason: "end_turn",
    tools_used: [],
    truncated: false,
    limit_reached: false,
    model: fallback ? null : MOCK_MODEL,
    fallback_used: fallback,
    provenance: provenance("assistant_chat", scenario, now, { dataAsOf: null }),
  };
  if (scenario === "abstention") {
    return { ...base, reply: `${note}${REFUSAL_REPLY}`, citations: [], refusal: { reason: "insufficient_sources" } };
  }
  if (scenario === "empty") {
    return { ...base, reply: `${note}${NO_SOURCE_REPLY}`, citations: [], refusal: null };
  }
  const prefix = fallback ? `${FALLBACK_NOTE}\n\n` : "";
  return { ...base, reply: `${note}${prefix}${answer.reply}`, citations: answer.citations, refusal: null };
}

/* ---------- 17. assistant_transcribe ---------- */

const TRANSCRIPTS = [
  "Quand faut-il arroser la parcelle d'oignons ?",
  "Les feuilles de tomate ont des taches brunes, que faire ?",
  "Quel engrais pour le chou en ce moment ?",
  "Quel est le prix de l'oignon au marché cette semaine ?",
] as const;

export function transcription(input: TranscribeInput, scenario: MockScenario, now: Date): Transcription {
  const key = hash32(input.audio_base64.slice(0, IMAGE_KEY_CHARS));
  const silent = scenario === "empty" || scenario === "abstention";
  const text = silent ? "" : (TRANSCRIPTS[key % TRANSCRIPTS.length] ?? "");
  const score = round(between(`asr:${key}`, 0.78, 0.93), 2);
  return {
    text,
    language: input.language_hint ?? "fr",
    duration_s: input.duration_s,
    provenance: provenance("assistant_transcribe", scenario, now, {
      confidence: silent ? NO_CONFIDENCE : probability(score, false),
      dataAsOf: null,
    }),
  };
}

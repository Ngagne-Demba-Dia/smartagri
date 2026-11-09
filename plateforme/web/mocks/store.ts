/**
 * État modifiable de la simulation : seuils demandés, alertes acquittées, retours sur les recommandations.
 * Vit sur globalThis (survit aux rechargements à chaud de Next) ; chaque écriture remplace l'objet.
 */
import type { RecommendationFeedback, SyncStatus, ThresholdPair, ThresholdState } from "@/lib/types";

import { DEFAULT_THRESHOLDS } from "./fixtures/places";

/** Délai simulé du passage du téléphone relais qui pousse les seuils au kit (ADR 007). */
export const THRESHOLD_SYNC_MS = 20_000;

interface ThresholdRecord {
  desired: ThresholdPair;
  commandId: string;
  requestedAt: number;
}

interface AlertRecord {
  status: "acknowledged" | "resolved";
  at: number;
}

interface MockState {
  thresholds: Readonly<Record<string, ThresholdRecord>>;
  alerts: Readonly<Record<string, AlertRecord>>;
  feedback: Readonly<Record<string, RecommendationFeedback>>;
  chats: Readonly<Record<string, readonly number[]>>;
  diagnoses: readonly DiagnosisLabel[];
  commandSeq: number;
}

export type DiagnosisLabel = "healthy" | "suspect" | "sick";

const KEY = Symbol.for("smartagri92.mock.store");
type Holder = Record<symbol, MockState | undefined>;

const empty = (): MockState => ({ thresholds: {}, alerts: {}, feedback: {}, chats: {}, diagnoses: [], commandSeq: 0 });

function read(): MockState {
  const holder = globalThis as unknown as Holder;
  const current = holder[KEY];
  if (current) return current;
  const fresh = empty();
  holder[KEY] = fresh;
  return fresh;
}

function write(next: MockState): MockState {
  (globalThis as unknown as Holder)[KEY] = next;
  return next;
}

export function resetStore(): void {
  write(empty());
}

const isoOf = (ms: number) => `${new Date(ms).toISOString().slice(0, 19)}Z`;

/** État de synchronisation : « pending » jusqu'au passage simulé du relais, puis « applied ». */
export function thresholdState(deviceId: string, now: Date): ThresholdState {
  const record = read().thresholds[deviceId];
  if (!record) {
    return { desired: { ...DEFAULT_THRESHOLDS }, reported: { ...DEFAULT_THRESHOLDS }, sync_status: "applied", command_id: null, updated_at: null };
  }
  const applied = now.getTime() - record.requestedAt >= THRESHOLD_SYNC_MS;
  const status: SyncStatus = applied ? "applied" : "pending";
  return {
    desired: { ...record.desired },
    reported: applied ? { ...record.desired } : null,
    sync_status: status,
    command_id: record.commandId,
    updated_at: isoOf(applied ? record.requestedAt + THRESHOLD_SYNC_MS : record.requestedAt),
  };
}

/** Seuils en vigueur sur le kit (ceux qui pilotent les séries simulées). */
export function effectiveThresholds(deviceId: string, now: Date): ThresholdPair {
  const state = thresholdState(deviceId, now);
  return state.reported ?? { ...DEFAULT_THRESHOLDS };
}

export function requestThresholds(deviceId: string, desired: ThresholdPair, now: Date): ThresholdState {
  const current = read();
  const seq = current.commandSeq + 1;
  const record: ThresholdRecord = { desired: { ...desired }, commandId: `cmd-mock-${seq}`, requestedAt: now.getTime() };
  write({ ...current, commandSeq: seq, thresholds: { ...current.thresholds, [deviceId]: record } });
  return thresholdState(deviceId, now);
}

export function alertOverride(alertId: string): { status: "acknowledged" | "resolved"; at: string } | null {
  const record = read().alerts[alertId];
  return record ? { status: record.status, at: isoOf(record.at) } : null;
}

export function acknowledgeAlert(alertId: string, now: Date): void {
  const current = read();
  write({ ...current, alerts: { ...current.alerts, [alertId]: { status: "acknowledged", at: now.getTime() } } });
}

export function feedbackFor(recommendationId: string): RecommendationFeedback | null {
  return read().feedback[recommendationId] ?? null;
}

export function recordFeedback(recommendationId: string, value: RecommendationFeedback): void {
  const current = read();
  write({ ...current, feedback: { ...current.feedback, [recommendationId]: value } });
}

export function feedbackCounts(): Record<RecommendationFeedback, number> {
  const counts: Record<RecommendationFeedback, number> = { followed: 0, partially_followed: 0, ignored: 0, not_applicable: 0 };
  for (const value of Object.values(read().feedback)) counts[value] += 1;
  return counts;
}

/** Limite simulée de l'assistant : messages par fenêtre glissante, par rôle de démonstration. */
export const CHAT_LIMIT = 8;
export const CHAT_WINDOW_MS = 60_000;

export type ChatQuota = { allowed: true } | { allowed: false; retryAfterS: number };

/** Enregistre un message s'il reste du quota ; sinon indique quand réessayer. */
export function recordChat(key: string, now: Date): ChatQuota {
  const current = read();
  const at = now.getTime();
  const recent = (current.chats[key] ?? []).filter((t) => at - t < CHAT_WINDOW_MS);
  if (recent.length >= CHAT_LIMIT) {
    const oldest = recent[0] ?? at;
    return { allowed: false, retryAfterS: Math.max(1, Math.ceil((oldest + CHAT_WINDOW_MS - at) / 1000)) };
  }
  write({ ...current, chats: { ...current.chats, [key]: [...recent, at] } });
  return { allowed: true };
}

/** Diagnostics enregistrés par POST /v1/diagnoses : renvoie le rang (identifiant dg-mock-N). */
export function recordDiagnosis(label: DiagnosisLabel): number {
  const current = read();
  const diagnoses = [...current.diagnoses, label];
  write({ ...current, diagnoses });
  return diagnoses.length;
}

export function diagnosisCounts(): Record<DiagnosisLabel, number> {
  const counts: Record<DiagnosisLabel, number> = { healthy: 0, suspect: 0, sick: 0 };
  for (const label of read().diagnoses) counts[label] += 1;
  return counts;
}

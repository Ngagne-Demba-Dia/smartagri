import "server-only";

import { MOCK_BASE, isMockMode } from "@/lib/mock-config";

/**
 * Seul point d'accès du BFF à l'API. AGRI_MOCK=1 : la requête est servie en mémoire par les
 * gestionnaires de mocks/ (aucun appel réseau) ; sinon fetch vers API_BASE_URL. Les composants React
 * n'en savent rien : retirer une simulation ne touche que mocks/ (doc 17 §3).
 */

/** URL interne de l'API (k8s : http://api.smartagri92.svc.cluster.local:8000). Jamais exposée au navigateur. */
export function apiBaseUrl(): string {
  const value = process.env.API_BASE_URL;
  if (!value) throw new Error("API_BASE_URL manquant : variable d'environnement obligatoire du BFF.");
  return value.replace(/\/+$/, "");
}

export function upstreamBase(): string {
  return isMockMode() ? MOCK_BASE : apiBaseUrl();
}

export async function upstreamFetch(input: string, init: RequestInit): Promise<Response> {
  if (!isMockMode()) return fetch(input, init);
  // `cache` n'a de sens que pour le fetch de Next : on ne le transmet pas au Request simulé.
  // Un membre `undefined` compte comme absent pour le constructeur de Request.
  const requestInit: RequestInit = { ...init, cache: undefined };
  const { handleMock } = await import("@/mocks");
  return handleMock(new Request(input, requestInit));
}

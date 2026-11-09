/**
 * Client typé du BFF (/api/v1/*) au-dessus de l'enveloppe {success, data, error, meta} (CONVENTIONS §5).
 * - Le navigateur ne voit jamais de jeton : les cookies httpOnly sont envoyés par le navigateur au BFF,
 *   qui ajoute l'en-tête Authorization vers l'API.
 * - Requêtes mutantes : en-tête X-Requested-With exigé par le BFF (doc 10 §7).
 * - 401 : un seul rafraîchissement partagé (single-flight) puis une seule nouvelle tentative ; deux
 *   rafraîchissements concurrents feraient détecter une réutilisation du jeton par l'API.
 */
import type { ApiErrorBody, ApiMeta, Envelope } from "./types";
import { CSRF_HEADER, CSRF_HEADER_VALUE } from "./session-cookies";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: Record<string, unknown> | undefined;

  constructor(code: string, message: string, status: number, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export interface ApiResult<T> {
  data: T;
  meta: ApiMeta | null;
}

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  query?: Record<string, QueryValue>;
  body?: unknown;
  signal?: AbortSignal;
}

export interface ApiClientConfig {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
  /** Appelé quand la session ne peut pas être renouvelée (redirection vers la connexion). */
  onSessionExpired?: () => void;
  timeoutMs?: number;
}

const DEFAULT_TIMEOUT_MS = 20_000;
const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Vérifie la forme de l'enveloppe ; toute autre réponse est une erreur BAD_RESPONSE. */
export function parseEnvelope<T>(payload: unknown, status: number): Envelope<T> {
  if (!isRecord(payload) || typeof payload.success !== "boolean" || !("data" in payload)) {
    throw new ApiError("BAD_RESPONSE", "Réponse inattendue du serveur.", status);
  }
  const error = payload.error;
  if (error !== null && error !== undefined) {
    if (!isRecord(error) || typeof error.code !== "string" || typeof error.message !== "string") {
      throw new ApiError("BAD_RESPONSE", "Erreur mal formée renvoyée par le serveur.", status);
    }
  }
  const meta = payload.meta;
  return {
    success: payload.success,
    data: (payload.data ?? null) as T | null,
    error: (error ?? null) as ApiErrorBody | null,
    meta: isRecord(meta) ? (meta as ApiMeta) : null,
  };
}

export function buildQuery(query: Record<string, QueryValue> | undefined): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.append(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export function createApiClient(config: ApiClientConfig = {}) {
  const baseUrl = config.baseUrl ?? "/api";
  const fetchImpl = config.fetchImpl ?? ((...args: Parameters<typeof fetch>) => fetch(...args));
  const timeoutMs = config.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  let refreshing: Promise<boolean> | null = null;

  async function send(path: string, options: RequestOptions): Promise<Response> {
    const method = options.method ?? "GET";
    const headers: Record<string, string> = { Accept: "application/json" };
    if (MUTATING.has(method)) headers[CSRF_HEADER] = CSRF_HEADER_VALUE;
    if (options.body !== undefined) headers["Content-Type"] = "application/json";

    // Délai et annulation combinés à la main : AbortSignal.any manque sur des navigateurs Android anciens.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const forwardAbort = () => controller.abort();
    options.signal?.addEventListener("abort", forwardAbort, { once: true });
    try {
      return await fetchImpl(`${baseUrl}${path}${buildQuery(options.query)}`, {
        method,
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        credentials: "same-origin",
        cache: "no-store",
        signal: controller.signal,
      });
    } catch (cause) {
      if (options.signal?.aborted) throw cause;
      throw new ApiError("NETWORK_ERROR", "Serveur injoignable. Vérifiez la connexion.", 0);
    } finally {
      clearTimeout(timer);
      options.signal?.removeEventListener("abort", forwardAbort);
    }
  }

  function refreshSession(): Promise<boolean> {
    refreshing ??= send("/auth/refresh", { method: "POST" })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
    return refreshing;
  }

  async function request<T>(path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
    // Les routes /auth/* (connexion, rafraîchissement) ne déclenchent ni rafraîchissement ni redirection.
    const isAuthRoute = path.startsWith("/auth/");
    let response = await send(path, options);
    if (response.status === 401 && !isAuthRoute && (await refreshSession())) {
      response = await send(path, options);
    }
    if (response.status === 401 && !isAuthRoute) {
      config.onSessionExpired?.();
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new ApiError("BAD_RESPONSE", "Réponse illisible du serveur.", response.status);
    }
    const envelope = parseEnvelope<T>(payload, response.status);
    if (!response.ok || !envelope.success || envelope.error) {
      const error = envelope.error ?? { code: "BAD_RESPONSE", message: "Requête refusée." };
      throw new ApiError(error.code, error.message, response.status, error.details);
    }
    return { data: envelope.data as T, meta: envelope.meta };
  }

  return {
    request,
    get: <T>(path: string, query?: Record<string, QueryValue>, signal?: AbortSignal) =>
      request<T>(path, { method: "GET", query, signal }),
    post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
    put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
    patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

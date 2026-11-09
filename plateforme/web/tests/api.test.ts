/**
 * Client du BFF (lib/api.ts) : enveloppe, en-tête anti-CSRF, rafraîchissement unique sur 401,
 * erreurs réseau et réponses illisibles. Le fetch est simulé ; aucun réseau.
 */
import { describe, expect, it, vi } from "vitest";

import { ApiError, buildQuery, createApiClient, parseEnvelope } from "@/lib/api";
import { CSRF_HEADER, CSRF_HEADER_VALUE } from "@/lib/session-cookies";

interface Sent {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string | undefined;
}

const ok = (data: unknown, meta: unknown = null) => Response.json({ success: true, data, error: null, meta });
const fail = (status: number, code: string, details?: Record<string, unknown>) =>
  Response.json(
    { success: false, data: null, error: { code, message: code, details }, meta: null },
    { status },
  );

/** fetch simulé : répond selon la route et journalise chaque requête. */
function fakeFetch(route: (sent: Sent, index: number) => Response | Promise<Response>) {
  const sent: Sent[] = [];
  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const entry: Sent = {
      url: String(input),
      method: init?.method ?? "GET",
      headers: { ...(init?.headers as Record<string, string>) },
      body: typeof init?.body === "string" ? init.body : undefined,
    };
    sent.push(entry);
    return route(entry, sent.length - 1);
  });
  return { sent, fetchImpl: fetchImpl as unknown as typeof fetch };
}

async function rejection(promise: Promise<unknown>): Promise<ApiError> {
  const error: unknown = await promise.then(
    () => null,
    (e: unknown) => e,
  );
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

describe("parseEnvelope", () => {
  it("lit une enveloppe valide et normalise data, error et meta", () => {
    expect(parseEnvelope({ success: true, data: { a: 1 }, error: null, meta: { page: 1 } }, 200)).toEqual({
      success: true,
      data: { a: 1 },
      error: null,
      meta: { page: 1 },
    });
    expect(parseEnvelope({ success: true, data: undefined, meta: [1] }, 200)).toEqual({
      success: true,
      data: null,
      error: null,
      meta: null,
    });
  });

  it.each([null, [], "texte", { data: 1 }, { success: "oui", data: 1 }, { success: true }])(
    "rejette une forme inattendue (%j)",
    (payload) => {
      expect(() => parseEnvelope(payload, 500)).toThrow(ApiError);
    },
  );

  it.each([{ code: 1, message: "x" }, { code: "X" }, "erreur", ["X"]])(
    "rejette une erreur mal formée (%j)",
    (error) => {
      try {
        parseEnvelope({ success: false, data: null, error }, 400);
        expect.unreachable();
      } catch (e) {
        expect(e).toBeInstanceOf(ApiError);
        expect([(e as ApiError).code, (e as ApiError).status]).toEqual(["BAD_RESPONSE", 400]);
      }
    },
  );
});

describe("buildQuery", () => {
  it("ignore undefined, null et la chaîne vide ; garde 0 et false", () => {
    expect(buildQuery({ a: "x y", b: undefined, c: null, d: "", e: 0, f: false })).toBe("?a=x+y&e=0&f=false");
  });

  it("renvoie une chaîne vide sans paramètre utile", () => {
    expect(buildQuery(undefined)).toBe("");
    expect(buildQuery({ a: undefined })).toBe("");
  });
});

describe("createApiClient", () => {
  it("GET : URL, requête et méta ; pas d'en-tête anti-CSRF", async () => {
    const { sent, fetchImpl } = fakeFetch(() => ok([1, 2], { total: 2 }));
    const client = createApiClient({ baseUrl: "/api", fetchImpl });
    const result = await client.get<number[]>("/v1/farms", { limit: 2, page: undefined });
    expect(result).toEqual({ data: [1, 2], meta: { total: 2 } });
    expect(sent[0]?.url).toBe("/api/v1/farms?limit=2");
    expect(sent[0]?.method).toBe("GET");
    expect(sent[0]?.headers[CSRF_HEADER]).toBeUndefined();
    expect(sent[0]?.headers.Accept).toBe("application/json");
  });

  it("POST, PUT et PATCH portent l'en-tête anti-CSRF et le corps JSON", async () => {
    const { sent, fetchImpl } = fakeFetch(() => ok({}));
    const client = createApiClient({ fetchImpl });
    await client.post("/v1/a", { x: 1 });
    await client.put("/v1/b", { y: 2 });
    await client.patch("/v1/c", { z: 3 });
    await client.post("/v1/d");
    expect(sent.map((s) => s.method)).toEqual(["POST", "PUT", "PATCH", "POST"]);
    expect(sent.every((s) => s.headers[CSRF_HEADER] === CSRF_HEADER_VALUE)).toBe(true);
    expect(sent[0]?.headers["Content-Type"]).toBe("application/json");
    expect(sent[0]?.body).toBe('{"x":1}');
    expect(sent[3]?.headers["Content-Type"]).toBeUndefined();
    expect(sent[3]?.body).toBeUndefined();
    expect(sent[0]?.url).toBe("/api/v1/a");
  });

  it("401 : un seul rafraîchissement pour des requêtes concurrentes, puis une nouvelle tentative", async () => {
    let refreshed = false;
    const { sent, fetchImpl } = fakeFetch((s) => {
      if (s.url.endsWith("/auth/refresh")) {
        refreshed = true;
        return ok({});
      }
      return refreshed ? ok(s.url) : fail(401, "UNAUTHENTICATED");
    });
    const onSessionExpired = vi.fn();
    const client = createApiClient({ fetchImpl, onSessionExpired });
    const results = await Promise.all([client.get("/v1/a"), client.get("/v1/b"), client.get("/v1/c")]);
    expect(results.map((r) => r.data)).toEqual(["/api/v1/a", "/api/v1/b", "/api/v1/c"]);
    expect(sent.filter((s) => s.url.endsWith("/auth/refresh"))).toHaveLength(1);
    expect(sent.find((s) => s.url.endsWith("/auth/refresh"))?.headers[CSRF_HEADER]).toBe(CSRF_HEADER_VALUE);
    expect(onSessionExpired).not.toHaveBeenCalled();
  });

  it("401 persistant : session expirée signalée, erreur de l'enveloppe remontée", async () => {
    const { sent, fetchImpl } = fakeFetch((s) =>
      s.url.endsWith("/auth/refresh") ? ok({}) : fail(401, "UNAUTHENTICATED"),
    );
    const onSessionExpired = vi.fn();
    const client = createApiClient({ fetchImpl, onSessionExpired });
    const error = await rejection(client.get("/v1/me"));
    expect([error.code, error.status]).toEqual(["UNAUTHENTICATED", 401]);
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
    expect(sent.map((s) => s.url)).toEqual(["/api/v1/me", "/api/auth/refresh", "/api/v1/me"]);
  });

  it("rafraîchissement refusé ou en échec réseau : pas de nouvelle tentative", async () => {
    for (const refresh of [
      () => fail(401, "UNAUTHENTICATED"),
      () => Promise.reject(new TypeError("réseau")),
    ]) {
      const { sent, fetchImpl } = fakeFetch((s) =>
        s.url.endsWith("/auth/refresh") ? refresh() : fail(401, "UNAUTHENTICATED"),
      );
      const onSessionExpired = vi.fn();
      const error = await rejection(createApiClient({ fetchImpl, onSessionExpired }).get("/v1/me"));
      expect(error.code).toBe("UNAUTHENTICATED");
      expect(sent).toHaveLength(2);
      expect(onSessionExpired).toHaveBeenCalledTimes(1);
    }
  });

  it("les routes /auth/* ne déclenchent ni rafraîchissement ni redirection", async () => {
    const { sent, fetchImpl } = fakeFetch(() => fail(401, "INVALID_CREDENTIALS"));
    const onSessionExpired = vi.fn();
    const error = await rejection(
      createApiClient({ fetchImpl, onSessionExpired }).post("/auth/login", { email: "x" }),
    );
    expect(error.code).toBe("INVALID_CREDENTIALS");
    expect(sent).toHaveLength(1);
    expect(onSessionExpired).not.toHaveBeenCalled();
  });

  it("erreur de l'enveloppe : code, statut et détails conservés", async () => {
    const { fetchImpl } = fakeFetch(() => fail(400, "THRESHOLDS_INVALID", { errors: ["gap_too_small"] }));
    const error = await rejection(createApiClient({ fetchImpl }).put("/v1/devices/d/thresholds", {}));
    expect([error.code, error.status, error.details]).toEqual([
      "THRESHOLDS_INVALID",
      400,
      { errors: ["gap_too_small"] },
    ]);
    expect(error.name).toBe("ApiError");
  });

  it("success false sans erreur, ou statut non 2xx avec success true : BAD_RESPONSE", async () => {
    const cases = [
      () => Response.json({ success: false, data: null, error: null, meta: null }),
      () => Response.json({ success: true, data: 1, error: null, meta: null }, { status: 500 }),
    ];
    for (const route of cases) {
      const { fetchImpl } = fakeFetch(route);
      expect((await rejection(createApiClient({ fetchImpl }).get("/v1/x"))).code).toBe("BAD_RESPONSE");
    }
  });

  it("corps illisible : BAD_RESPONSE avec le statut HTTP", async () => {
    const { fetchImpl } = fakeFetch(() => new Response("<html>passerelle</html>", { status: 502 }));
    const error = await rejection(createApiClient({ fetchImpl }).get("/v1/x"));
    expect([error.code, error.status]).toEqual(["BAD_RESPONSE", 502]);
  });

  it("échec réseau : NETWORK_ERROR de statut 0", async () => {
    const { fetchImpl } = fakeFetch(() => Promise.reject(new TypeError("Failed to fetch")));
    const error = await rejection(createApiClient({ fetchImpl }).get("/v1/x"));
    expect([error.code, error.status]).toEqual(["NETWORK_ERROR", 0]);
  });

  it("annulation par l'appelant : l'erreur d'origine est relancée telle quelle", async () => {
    const controller = new AbortController();
    const abortError = new DOMException("annulé", "AbortError");
    const fetchImpl = ((_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(abortError));
      })) as typeof fetch;
    const pending = createApiClient({ fetchImpl }).get("/v1/x", undefined, controller.signal);
    controller.abort();
    await expect(pending).rejects.toBe(abortError);
  });

  it("délai dépassé : la requête est annulée et devient NETWORK_ERROR", async () => {
    const fetchImpl = ((_input: RequestInfo | URL, init?: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("délai", "AbortError")));
      })) as typeof fetch;
    const error = await rejection(createApiClient({ fetchImpl, timeoutMs: 5 }).get("/v1/x"));
    expect(error.code).toBe("NETWORK_ERROR");
  });

  it("request() accepte DELETE avec l'en-tête anti-CSRF", async () => {
    const { sent, fetchImpl } = fakeFetch(() => ok(null));
    const result = await createApiClient({ fetchImpl }).request("/v1/x", { method: "DELETE" });
    expect(result.data).toBeNull();
    expect(sent[0]?.headers[CSRF_HEADER]).toBe(CSRF_HEADER_VALUE);
  });
});

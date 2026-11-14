/**
 * Contrat live de GET /v1/fields/{id}/irrigation-need (service 3, doc 16 §9.1) : la réponse de l'API réelle
 * doit satisfaire le schéma Zod du Frontend RC, par appel direct puis à travers le BFF en mode hybride
 * (AGRI_MOCK=1 + AGRI_SERVICES=irrigation_need=real). Lancer : `npm run test:live` (voir vitest.live.config.ts).
 */
import { readFileSync } from "node:fs";

import { NextRequest } from "next/server";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { IrrigationNeedSchema } from "@/lib/contracts/field";
import { ACCESS_COOKIE } from "@/lib/session-cookies";

vi.mock("server-only", () => ({}));

interface Stack {
  api_url: string;
  username: string;
  password: string;
  weather: { rain_mm: number; et0_mm: number };
}

const stack: Stack = JSON.parse(readFileSync(process.env.LIVE_STACK_FILE ?? ".live-stack.json", "utf8"));
const GET_NEED = (fieldId: string): string => `/v1/fields/${fieldId}/irrigation-need`;

let token = "";
let fieldId = "";
let areaHa = 0;

interface Envelope<T = unknown> {
  success: boolean;
  data: T;
  error: { code: string } | null;
}

async function api<T = unknown>(path: string, init?: RequestInit): Promise<{ status: number; body: Envelope<T> }> {
  const response = await fetch(`${stack.api_url}${path}`, init);
  return { status: response.status, body: (await response.json()) as Envelope<T> };
}

const authed = (): RequestInit => ({ headers: { Authorization: `Bearer ${token}` } });

beforeAll(async () => {
  const login = await api<{ access_token: string }>("/v1/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: stack.username, password: stack.password }),
  });
  expect(login.status).toBe(200);
  token = login.body.data.access_token;
  const farms = await api<{ id: string }[]>("/v1/farms", authed());
  const farmId = farms.body.data[0]?.id ?? "";
  const fields = await api<{ id: string; area_ha: number }[]>(`/v1/farms/${farmId}/fields`, authed());
  fieldId = fields.body.data[0]?.id ?? "";
  areaHa = fields.body.data[0]?.area_ha ?? 0;
  expect(fieldId).not.toBe("");
});

afterAll(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("contrat live — API directe", () => {
  it("l'enveloppe et la charge utile satisfont IrrigationNeedSchema", async () => {
    const { status, body } = await api(GET_NEED(fieldId), authed());
    expect(status).toBe(200);
    expect(body.success).toBe(true);
    const parsed = IrrigationNeedSchema.safeParse(body.data);
    expect(parsed.success, JSON.stringify(parsed.error?.issues)).toBe(true);
  });

  it("le report de l'arrosage suit la pluie annoncée par la météo", async () => {
    const { body } = await api(GET_NEED(fieldId), authed());
    const need = IrrigationNeedSchema.parse(body.data);
    expect(need.field_id).toBe(fieldId);
    expect(need.window_hours).toBe(24);
    expect(need.rain_expected_mm).toBe(stack.weather.rain_mm);
    expect(need.need_mm).toBeGreaterThan(0);
    expect(need.defer).toBe(stack.weather.rain_mm >= 5);
    expect(need.defer_reason).toMatch(/Pluie annoncée/);
    expect(need.volume_m3).toBeCloseTo(need.need_mm * areaHa * 10, 0);
    expect(need.provenance).toMatchObject({ source: "rules", fallback_step: 2, stale: false });
    expect(need.provenance.confidence.kind).toBe("none");
  });

  it("le schéma n'est pas vacuous : une charge utile altérée est refusée", async () => {
    const { body } = await api<Record<string, unknown>>(GET_NEED(fieldId), authed());
    expect(IrrigationNeedSchema.safeParse({ ...body.data, need_mm: -1 }).success).toBe(false);
    expect(IrrigationNeedSchema.safeParse({ ...body.data, provenance: undefined }).success).toBe(false);
    expect(IrrigationNeedSchema.safeParse({ ...body.data, window_hours: 48 }).success).toBe(false);
  });

  it("parcelle inconnue ou sans jeton : erreurs d'enveloppe, pas de charge utile", async () => {
    const unknown = await api(GET_NEED("00000000-0000-0000-0000-000000000000"), authed());
    expect(unknown.status).toBe(404);
    expect(unknown.body).toMatchObject({ success: false, data: null, error: { code: "NOT_FOUND" } });
    expect((await api(GET_NEED(fieldId))).status).toBe(401);
  });
});

describe("contrat live — à travers le BFF en mode hybride", () => {
  async function throughBff(path: string): Promise<Response> {
    const { GET } = await import("@/app/api/v1/[...path]/route");
    const request = new NextRequest(`http://localhost:3000/api${path}`, {
      headers: { cookie: `${ACCESS_COOKIE}=${token}` },
    });
    return GET(request, { params: Promise.resolve({ path: path.replace(/^\/v1\//, "").split("/") }) });
  }

  it("irrigation_need=real : la requête part vers l'API réelle et la réponse satisfait le schéma", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "irrigation_need=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);
    const network = vi.spyOn(globalThis, "fetch");
    const response = await throughBff(GET_NEED(fieldId));
    expect(response.status).toBe(200);
    const parsed = IrrigationNeedSchema.safeParse((await response.json()).data);
    expect(parsed.success, JSON.stringify(parsed.error?.issues)).toBe(true);
    expect(network).toHaveBeenCalledTimes(1);
    expect(String(network.mock.calls[0]?.[0])).toBe(`${stack.api_url}${GET_NEED(fieldId)}`);
  });

  it("un autre service reste simulé : aucun appel réseau pour pest_risk", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "irrigation_need=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);
    const network = vi.spyOn(globalThis, "fetch");
    const response = await throughBff(`/v1/fields/${fieldId}/pest-risk`);
    expect(network).not.toHaveBeenCalled(); // servi en mémoire par mocks/ (404 : parcelle réelle inconnue du mock)
    expect([401, 404]).toContain(response.status);
  });

  it("sans exception AGRI_SERVICES et AGRI_MOCK=0, tout part vers l'API réelle (comportement d'avant)", async () => {
    vi.stubEnv("AGRI_MOCK", "0");
    vi.stubEnv("AGRI_SERVICES", "");
    vi.stubEnv("API_BASE_URL", stack.api_url);
    const network = vi.spyOn(globalThis, "fetch");
    const response = await throughBff(GET_NEED(fieldId));
    expect(response.status).toBe(200);
    expect(IrrigationNeedSchema.safeParse((await response.json()).data).success).toBe(true);
    expect(network).toHaveBeenCalledTimes(1);
  });
});

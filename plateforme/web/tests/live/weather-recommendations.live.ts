/**
 * Test de contrat live Sprint D2 : `weather` + `recommendations` + mapping d'identifiants hybrides
 * à travers le BFF Next (`app/api/v1/[...path]/route.ts`) contre FastAPI réelle + SQLite jetable.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { NextRequest } from "next/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { PestRiskSchema, RecommendationListSchema, RecommendationSchema, WeatherSchema } from "@/lib/contracts/field";
import { DEMO_UUID_BY_SLUG } from "@/lib/service-mode";
import { ACCESS_COOKIE, CSRF_HEADER, CSRF_HEADER_VALUE } from "@/lib/session-cookies";

vi.mock("server-only", () => ({}));

interface LiveStack {
  api_url: string;
  username: string;
  password: string;
  weather: { rain_mm: number; et0_mm: number };
}

const ORIGIN = "http://localhost:3000";
const UNKNOWN_FIELD = "00000000-0000-0000-0000-000000000000";

let stack: LiveStack;
let token: string;
let fieldId: string;

async function bff(method: string, apiPath: string, query = "", body?: unknown): Promise<Response> {
  const { GET, POST } = await import("@/app/api/v1/[...path]/route");
  const headers: Record<string, string> = {
    cookie: `${ACCESS_COOKIE}=${token}`,
  };
  if (method !== "GET") {
    headers["content-type"] = "application/json";
    headers["origin"] = ORIGIN;
    headers[CSRF_HEADER] = CSRF_HEADER_VALUE;
  }
  const req = new NextRequest(`${ORIGIN}/api/${apiPath}${query}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const handler = method === "POST" ? POST : GET;
  return handler(req, { params: Promise.resolve({ path: apiPath.split("/").slice(1) }) });
}

beforeAll(async () => {
  stack = JSON.parse(readFileSync(resolve(process.cwd(), ".live-stack.json"), "utf-8")) as LiveStack;
  const login = await fetch(`${stack.api_url}/v1/auth/token`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username: stack.username, password: stack.password }),
  });
  expect(login.status).toBe(200);
  token = ((await login.json()) as { data: { access_token: string } }).data.access_token;

  const farms = await fetch(`${stack.api_url}/v1/farms`, { headers: { authorization: `Bearer ${token}` } });
  const farmId = ((await farms.json()) as { data: [{ id: string }] }).data[0].id;
  const fields = await fetch(`${stack.api_url}/v1/farms/${farmId}/fields`, {
    headers: { authorization: `Bearer ${token}` },
  });
  fieldId = ((await fields.json()) as { data: [{ id: string }] }).data[0].id;
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("contrat live D2 : weather, recommendations et mapping hybride (BFF → FastAPI)", () => {
  it("le seed backend utilise l'UUID canonique mappé à fld-mboro-1 et accepte aussi le slug", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "weather=real,recommendations=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    expect(fieldId).toBe(DEMO_UUID_BY_SLUG["fld-mboro-1"]);

    // Appel avec le slug mock `fld-mboro-1` routé vers le backend réel
    const bySlug = await bff("GET", "v1/fields/fld-mboro-1/weather", "?days=3");
    expect(bySlug.status).toBe(200);
    const parsedSlug = WeatherSchema.parse(((await bySlug.json()) as { data: unknown }).data);
    expect(parsedSlug.field_id).toBe(fieldId);
    expect(parsedSlug.days).toHaveLength(3);
  });

  it("weather=real valide WeatherSchema (provenance open_meteo, cache / provider)", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "weather=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    const response = await bff("GET", `v1/fields/${fieldId}/weather`, "?days=5");
    expect(response.status).toBe(200);
    const body = (await response.json()) as { data: unknown };
    const parsed = WeatherSchema.parse(body.data);

    expect(parsed.field_id).toBe(fieldId);
    expect(parsed.provider).toBe("open-meteo");
    expect(parsed.days).toHaveLength(5);
    expect(parsed.days[0]?.precipitation_mm).toBe(stack.weather.rain_mm);
    expect(parsed.days[0]?.et0_mm).toBe(stack.weather.et0_mm);
    expect(parsed.days[0]?.et0_hargreaves_mm).not.toBeNull();
    expect(parsed.provenance?.source).toBe("rules");
    expect(["provider", "cache"]).toContain(parsed.source);
  });

  it("recommendations=real valide RecommendationListSchema et POST feedback valide RecommendationSchema", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "recommendations=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    const response = await bff("GET", `v1/fields/${fieldId}/recommendations`);
    expect(response.status).toBe(200);
    const listBody = (await response.json()) as { data: unknown };
    const parsedList = RecommendationListSchema.parse(listBody.data);

    expect(parsedList.length).toBeGreaterThanOrEqual(2);
    const irr = parsedList.find((r) => r.kind === "irrigation");
    const fert = parsedList.find((r) => r.kind === "fertilization");
    expect(irr).toBeDefined();
    expect(fert).toBeDefined();
    expect(irr?.provenance?.model_name).toBe("irrigation_fao56");
    expect(irr?.provenance?.source).toBe("rules");
    expect(irr?.provenance?.fallback_step).toBe(2);
    expect(fert?.provenance?.model_name).toBe("fertility_rules");

    // Enregistrement du retour utilisateur (POST /v1/recommendations/{id}/feedback)
    const fbRes = await bff("POST", `v1/recommendations/${irr!.id}/feedback`, "", { feedback: "followed" });
    expect(fbRes.status).toBe(200);
    const fbData = ((await fbRes.json()) as { data: unknown }).data;
    const parsedFb = RecommendationSchema.parse(fbData);
    expect(parsedFb.id).toBe(irr!.id);
    expect(parsedFb.kind).toBe("irrigation");
  });

  it("cohabitation hybride : un service resté en mock accepte l'UUID canonique réel sans 404", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "weather=real,recommendations=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    const { tokenPair } = await import("@/mocks/auth");
    const savedToken = token;
    try {
      token = tokenPair("admin").access_token;
      // pest_risk est toujours en mock, mais appelé avec l'UUID réel `fieldId`
      const mockRes = await bff("GET", `v1/fields/${fieldId}/pest-risk`);
      expect(mockRes.status).toBe(200);
      const parsed = PestRiskSchema.parse(((await mockRes.json()) as { data: unknown }).data);
      expect(parsed.pests.length).toBeGreaterThan(0);

      const mock404 = await bff("GET", `v1/fields/${UNKNOWN_FIELD}/pest-risk`);
      expect(mock404.status).toBe(404);
    } finally {
      token = savedToken;
    }

    // Un UUID réellement inconnu renvoie bien 404 en réel aussi
    const real404 = await bff("GET", `v1/fields/${UNKNOWN_FIELD}/weather`);
    expect(real404.status).toBe(404);
  });
});

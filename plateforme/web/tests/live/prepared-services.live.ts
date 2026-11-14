/**
 * Test de contrat live Sprints D4, D5 et D6 :
 * - D4 : `fertilization` (`GET /v1/fields/{id}/fertilization`) et `pest_risk` (`GET /v1/fields/{id}/pest-risk`)
 * - D5 : `disease_diagnosis` (`POST /v1/diagnoses/analyze` : 413, 404 hors scope, 503 MODEL_UNAVAILABLE honnête)
 * - D6 : `assistant_transcribe` (`POST /v1/assistant/transcribe` : 413, 422 durée > 60 s, 503 MODEL_UNAVAILABLE)
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { NextRequest } from "next/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { FertilizationSchema, PestRiskSchema } from "@/lib/contracts/field";
import { ACCESS_COOKIE, CSRF_HEADER, CSRF_HEADER_VALUE } from "@/lib/session-cookies";

vi.mock("server-only", () => ({}));

interface LiveStack {
  api_url: string;
  username: string;
  password: string;
}

const ORIGIN = "http://localhost:3000";

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

describe("contrat live D4, D5, D6 : services préparés (BFF → FastAPI)", () => {
  it("D4 : fertilization=real et pest_risk=real valident FertilizationSchema et PestRiskSchema (sans inventer de doses)", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "fertilization=real,pest_risk=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    const fertRes = await bff("GET", `v1/fields/${fieldId}/fertilization`);
    expect(fertRes.status).toBe(200);
    const fertParsed = FertilizationSchema.parse(((await fertRes.json()) as { data: unknown }).data);
    expect(fertParsed.field_id).toBe(fieldId);
    expect(fertParsed.indicative).toBe(true);
    expect(fertParsed.n_kg_ha).toBeNull();
    expect(fertParsed.p_kg_ha).toBeNull();
    expect(fertParsed.k_kg_ha).toBeNull();
    expect(fertParsed.npk_class).toBe("moyen");
    expect(fertParsed.provenance.model_name).toBe("fert_reco");
    expect(fertParsed.provenance.source).toBe("rules");

    const pestRes = await bff("GET", `v1/fields/${fieldId}/pest-risk`);
    expect(pestRes.status).toBe(200);
    const pestParsed = PestRiskSchema.parse(((await pestRes.json()) as { data: unknown }).data);
    expect(pestParsed.field_id).toBe(fieldId);
    expect(pestParsed.pests).toEqual([]);
    expect(pestParsed.provenance.model_name).toBe("risk_rules");
    expect(pestParsed.provenance.source).toBe("rules");
  });

  it("D5 : diagnosis_analyze=real renvoie 503 MODEL_UNAVAILABLE sans bundle vis_disease et 404 hors scope", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "diagnosis_analyze=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    const smallImage = Buffer.from("fake-jpeg").toString("base64");
    const res503 = await bff("POST", "v1/diagnoses/analyze", "", {
      image_base64: smallImage,
      content_type: "image/jpeg",
      field_id: fieldId,
      device_id: null,
      captured_at: new Date().toISOString(),
    });
    expect(res503.status).toBe(503);
    const err503 = (await res503.json()) as { error: { code: string } };
    expect(err503.error.code).toBe("MODEL_UNAVAILABLE");

    const res404 = await bff("POST", "v1/diagnoses/analyze", "", {
      image_base64: smallImage,
      content_type: "image/jpeg",
      field_id: "00000000-0000-0000-0000-000000000000",
      device_id: null,
      captured_at: new Date().toISOString(),
    });
    expect(res404.status).toBe(404);
  });

  it("D6 : assistant_transcribe=real renvoie 503 MODEL_UNAVAILABLE sans fournisseur ASR et 422 au-delà de 60 s", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "assistant_transcribe=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    const smallAudio = Buffer.from("fake-opus").toString("base64");
    const res503 = await bff("POST", "v1/assistant/transcribe", "", {
      audio_base64: smallAudio,
      content_type: "audio/webm;codecs=opus",
      duration_s: 12,
      language_hint: "wo",
    });
    expect(res503.status).toBe(503);
    const err503 = (await res503.json()) as { error: { code: string } };
    expect(err503.error.code).toBe("MODEL_UNAVAILABLE");

    const res422 = await bff("POST", "v1/assistant/transcribe", "", {
      audio_base64: smallAudio,
      content_type: "audio/webm;codecs=opus",
      duration_s: 90,
      language_hint: "wo",
    });
    expect(res422.status).toBe(422);
  });
});

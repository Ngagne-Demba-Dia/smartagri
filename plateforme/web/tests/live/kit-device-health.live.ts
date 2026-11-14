/**
 * Test de contrat live Sprint D3 : `kit_parameters` + `device_health` (+ alertes)
 * à travers le BFF Next (`app/api/v1/[...path]/route.ts`) contre FastAPI réelle + SQLite jetable.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { NextRequest } from "next/server";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { AlertListSchema, DeviceHealthSchema, KitParametersSchema } from "@/lib/contracts/device";
import { DEMO_UUID_BY_SLUG } from "@/lib/service-mode";
import { ACCESS_COOKIE, CSRF_HEADER, CSRF_HEADER_VALUE } from "@/lib/session-cookies";

vi.mock("server-only", () => ({}));

interface LiveStack {
  api_url: string;
  username: string;
  password: string;
}

const ORIGIN = "http://localhost:3000";
const UNKNOWN_DEVICE = "00000000-0000-0000-0000-000000000000";

let stack: LiveStack;
let token: string;
let deviceId: string;

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

  const devices = await fetch(`${stack.api_url}/v1/devices`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(devices.status).toBe(200);
  deviceId = ((await devices.json()) as { data: [{ id: string }] }).data[0].id;
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("contrat live D3 : kit_parameters et device_health (BFF → FastAPI)", () => {
  it("kit_parameters=real valide KitParametersSchema (GET + POST ack, UUID et slug dev-0001)", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "kit_parameters=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    expect(deviceId).toBe(DEMO_UUID_BY_SLUG["dev-0001"]);

    // Consultation via le slug démo `dev-0001`
    const response = await bff("GET", "v1/devices/dev-0001/parameters");
    expect(response.status).toBe(200);
    const body = (await response.json()) as { data: unknown };
    const parsed = KitParametersSchema.parse(body.data);

    expect(parsed.device_id).toBe(deviceId);
    expect(parsed.version).toBeGreaterThanOrEqual(1);
    expect(parsed.seuils).toEqual({ start: 28, stop: 55 });
    expect(parsed.npk).toEqual({ n: 20, p: 10, k: 80 });
    expect(parsed.agro?.culture).toBe("onion");
    expect(parsed.provenance.seuils?.model_name).toBe("irr_water_balance");
    expect(parsed.provenance.seuils?.source).toBe("rules");
    expect(parsed.provenance.npk?.model_name).toBe("fert_reco");
    expect(parsed.provenance.agro?.model_name).toBe("phenology_stage");

    // Acquittement via POST /v1/devices/{id}/parameters/ack
    const ackRes = await bff("POST", `v1/devices/${deviceId}/parameters/ack`, "", {
      version: parsed.version,
      applied: true,
    });
    expect(ackRes.status).toBe(200);
    const ackParsed = KitParametersSchema.parse(((await ackRes.json()) as { data: unknown }).data);
    expect(ackParsed.applied).toBe(true);
  });

  it("device_health=real valide DeviceHealthSchema et AlertListSchema", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "device_health=real");
    vi.stubEnv("API_BASE_URL", stack.api_url);

    const response = await bff("GET", `v1/devices/${deviceId}/health`);
    expect(response.status).toBe(200);
    const body = (await response.json()) as { data: unknown };
    const parsed = DeviceHealthSchema.parse(body.data);

    expect(parsed.device_id).toBe(deviceId);
    expect(parsed.sensors).toHaveLength(6);
    expect(parsed.sensors.find((s) => s.sensor === "soil")?.state).toBe("ok");
    expect(parsed.sensors.find((s) => s.sensor === "bme")?.state).toBe("ok");
    expect(parsed.sensors.find((s) => s.sensor === "npk")?.state).toBe("ok");
    expect(parsed.sensors.find((s) => s.sensor === "flow")?.state).toBe("ok");
    expect(parsed.pump_failure_48h).toBeNull();
    expect(parsed.provenance?.model_name).toBe("anomaly_rules");
    expect(parsed.provenance?.source).toBe("rules");
    expect(parsed.provenance?.stale).toBe(false);

    // Route d'alertes rattachée à device_health
    const alertsRes = await bff("GET", "v1/alerts");
    expect(alertsRes.status).toBe(200);
    const alertsParsed = AlertListSchema.parse(((await alertsRes.json()) as { data: unknown }).data);
    expect(Array.isArray(alertsParsed)).toBe(true);

    // Kit inconnu -> 404 NOT_FOUND
    const missing = await bff("GET", `v1/devices/${UNKNOWN_DEVICE}/health`);
    expect(missing.status).toBe(404);
  });
});

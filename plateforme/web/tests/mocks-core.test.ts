/**
 * Routes du socle simulées (doc 16 §9.5) : session, référentiel, kits, mesures, seuils, export CSV,
 * et module de pilotage des scénarios. Ces routes n'ont pas de scénario d'IA.
 */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { Device, DeviceDetail, Farm, Me, MeasurementSeries, ThresholdState } from "@/lib/types";
import { resetScenarios, resetStore } from "@/mocks";
import { DEMO_PASSWORD } from "@/mocks/auth";
import { clearScenario, isScenario, isServiceId, scenarioFor, setScenario, snapshot } from "@/mocks/scenario";
import { THRESHOLD_SYNC_MS, effectiveThresholds, thresholdState } from "@/mocks/store";

import { call, get, post, put, readEnvelope, type Role } from "./helpers";

process.env.AGRI_MOCK_LATENCY = "0";

beforeEach(() => {
  resetScenarios();
  resetStore();
});

async function dataOf<T>(path: string, role: Role = "admin"): Promise<T> {
  const response = await call(get(path), role);
  expect(response.status).toBe(200);
  return (await readEnvelope(response)).data as T;
}

async function errorCode(response: Response): Promise<string | undefined> {
  return (await readEnvelope(response)).error?.code;
}

describe("authentification simulée", () => {
  it("délivre une paire de jetons pour un compte de démonstration", async () => {
    const response = await call(
      post("/v1/auth/token", { username: " Agronome@demo.sn ", password: DEMO_PASSWORD }),
      null,
    );
    expect(response.status).toBe(200);
    const tokens = (await readEnvelope(response)).data as {
      access_token: string;
      refresh_token: string;
      expires_in: number;
    };
    expect(tokens.access_token).toBe("mock-access-agronomist");
    expect(tokens.refresh_token).toBe("mock-refresh-agronomist");
    expect(tokens.expires_in).toBeGreaterThan(0);
  });

  it("refuse un mot de passe faux (401) et des champs manquants (422)", async () => {
    const wrong = await call(post("/v1/auth/token", { username: "admin@demo.sn", password: "x" }), null);
    expect(wrong.status).toBe(401);
    expect(await errorCode(wrong)).toBe("INVALID_CREDENTIALS");
    const missing = await call(post("/v1/auth/token", { username: "admin@demo.sn" }), null);
    expect(missing.status).toBe(422);
    expect((await call(post("/v1/auth/token"), null)).status).toBe(422);
  });

  it("renouvelle la session avec un jeton de rafraîchissement valide, sinon 401", async () => {
    const refreshed = await call(post("/v1/auth/refresh", { refresh_token: "mock-refresh-farmer" }), null);
    expect(((await readEnvelope(refreshed)).data as { access_token: string }).access_token).toBe(
      "mock-access-farmer",
    );
    for (const token of ["mock-refresh-pirate", "mock-access-farmer", 42]) {
      const response = await call(post("/v1/auth/refresh", { refresh_token: token }), null);
      expect(response.status).toBe(401);
      expect(await errorCode(response)).toBe("UNAUTHENTICATED");
    }
  });

  it("accepte la déconnexion sans corps", async () => {
    expect((await call(post("/v1/auth/logout"), null)).status).toBe(200);
  });

  it("refuse un jeton d'accès d'un rôle inconnu (401)", async () => {
    const { handleMock } = await import("@/mocks");
    const { MOCK_BASE } = await import("@/lib/mock-config");
    const response = await handleMock(
      new Request(`${MOCK_BASE}/v1/me`, { headers: { authorization: "Bearer mock-access-root" } }),
    );
    expect(response.status).toBe(401);
  });
});

describe("référentiel", () => {
  it("/v1/me nomme des rôles, jamais des personnes", async () => {
    const me = await dataOf<Me>("/v1/me", "coop_manager");
    expect(me.full_name).toBeNull();
    expect(me.memberships.map((m) => m.role)).toEqual(["coop_manager"]);
  });

  it("/v1/farms : périmètre par organisation et pagination bornée", async () => {
    expect((await dataOf<Farm[]>("/v1/farms", "farmer")).map((f) => f.id)).toEqual(["farm-ndiol"]);
    const response = await call(get("/v1/farms?limit=2"));
    const body = await readEnvelope(response);
    expect((body.data as Farm[]).length).toBe(2);
    expect(body.meta).toMatchObject({ total: 3, page: 1, limit: 2 });
    for (const limit of ["0", "501", "deux"])
      expect((await call(get(`/v1/farms?limit=${limit}`))).status).toBe(422);
  });

  it("parcelles, cycles, campagnes et matériel du périmètre", async () => {
    expect((await dataOf<unknown[]>("/v1/farms/farm-mboro/fields")).length).toBe(3);
    expect(await dataOf<{ id: string }>("/v1/fields/fld-mboro-1")).toMatchObject({ id: "fld-mboro-1" });
    expect((await dataOf<unknown[]>("/v1/fields/fld-mboro-1/crop-cycles")).length).toBeGreaterThan(0);
    expect(
      (await dataOf<Array<{ organization_id: string }>>("/v1/campaigns", "farmer")).every(
        (c) => c.organization_id === "org-demo-ndiol",
      ),
    ).toBe(true);
    expect((await dataOf<unknown[]>("/v1/equipment")).length).toBeGreaterThan(0);
  });

  it.each([
    "/v1/farms/farm-mboro/fields",
    "/v1/fields/fld-mboro-1",
    "/v1/fields/fld-mboro-1/crop-cycles",
    "/v1/devices/dev-0001",
  ])("hors périmètre → 404 : %s", async (path) => {
    const response = await call(get(path), "farmer");
    expect(response.status).toBe(404);
    expect(await errorCode(response)).toBe("NOT_FOUND");
  });
});

describe("kits et mesures", () => {
  it("filtre les kits par statut et refuse un statut inconnu (422)", async () => {
    const inactive = await dataOf<Device[]>("/v1/devices?status=inactive");
    expect(inactive.map((d) => d.id)).toEqual(["dev-0004"]);
    expect((await call(get("/v1/devices?status=perdu"))).status).toBe(422);
  });

  it("détaille un kit avec sa dernière mesure", async () => {
    const detail = await dataOf<DeviceDetail>("/v1/devices/dev-0001");
    expect(detail.serial).toBe("SA92-0001");
    expect(detail.latest_measurement).not.toBeNull();
  });

  it("sert une série agrégée avec meta.count et meta.truncated", async () => {
    const response = await call(get("/v1/devices/dev-0001/measurements?bucket=1h"));
    const body = await readEnvelope(response);
    const series = body.data as MeasurementSeries;
    expect(series.bucket).toBe("1h");
    expect(body.meta).toMatchObject({ count: series.rows.length, truncated: false });
    expect(series.rows.length).toBeGreaterThan(0);
  });

  it("tronque une série brute trop longue aux 400 points les plus récents", async () => {
    const body = await readEnvelope(
      await call(get("/v1/devices/dev-0001/measurements?bucket=raw&from=2026-09-01&to=2026-11-01")),
    );
    expect(body.meta).toMatchObject({ count: 400, truncated: true });
  });

  it.each([
    ["bucket=2h", 422, "INVALID_BUCKET"],
    ["from=2026-11-05&to=2026-11-01", 422, "VALIDATION_ERROR"],
    ["from=hier", 422, "VALIDATION_ERROR"],
  ])("refuse ?%s", async (query, status, code) => {
    const response = await call(get(`/v1/devices/dev-0001/measurements?${query}`));
    expect(response.status).toBe(status);
    expect(await errorCode(response)).toBe(code);
  });

  it("mesures d'un kit inconnu → 404", async () => {
    expect((await call(get("/v1/devices/dev-9999/measurements"))).status).toBe(404);
  });
});

describe("seuils d'irrigation", () => {
  it("applique les seuils par défaut tant que rien n'est demandé", async () => {
    const state = await dataOf<ThresholdState>("/v1/devices/dev-0001/thresholds");
    expect(state).toMatchObject({
      desired: { start_pct: 30, stop_pct: 60 },
      sync_status: "applied",
      command_id: null,
    });
  });

  it("met la demande en attente puis l'applique au passage simulé du relais", async () => {
    const response = await call(
      put("/v1/devices/dev-0001/thresholds", { start: "35", stop: 70 }),
      "coop_manager",
    );
    const pending = (await readEnvelope(response)).data as ThresholdState;
    expect(pending).toMatchObject({
      desired: { start_pct: 35, stop_pct: 70 },
      reported: null,
      sync_status: "pending",
      command_id: "cmd-mock-1",
    });
    expect(effectiveThresholds("dev-0001", new Date())).toEqual({ start_pct: 30, stop_pct: 60 });
    const later = new Date(Date.now() + THRESHOLD_SYNC_MS + 1_000);
    expect(thresholdState("dev-0001", later)).toMatchObject({
      sync_status: "applied",
      reported: { start_pct: 35, stop_pct: 70 },
    });
    expect(effectiveThresholds("dev-0001", later)).toEqual({ start_pct: 35, stop_pct: 70 });
  });

  it("refuse l'agronome (403) et un kit hors périmètre (404)", async () => {
    expect(
      (await call(put("/v1/devices/dev-0001/thresholds", { start: 30, stop: 60 }), "agronomist")).status,
    ).toBe(403);
    expect(
      (await call(put("/v1/devices/dev-0001/thresholds", { start: 30, stop: 60 }), "farmer")).status,
    ).toBe(404);
    expect((await call(get("/v1/devices/dev-0001/thresholds"), "farmer")).status).toBe(404);
  });

  it.each([
    [{ start: 40, stop: 42 }, "gap_too_small"],
    [{ start: 30, stop: 101 }, "stop_above_max"],
    [{ start: 30.5, stop: 60 }, "not_integer"],
    [{ start: true, stop: 60 }, "not_integer"],
    [null, "not_integer"],
  ])("refuse %j (400 THRESHOLDS_INVALID, %s)", async (body, code) => {
    const response = await call(put("/v1/devices/dev-0101/thresholds", body ?? undefined), "farmer");
    expect(response.status).toBe(400);
    const error = (await readEnvelope(response)).error;
    expect(error?.code).toBe("THRESHOLDS_INVALID");
    expect((error?.details?.errors as Array<{ code: string }>).map((e) => e.code)).toContain(code);
  });
});

describe("export CSV du rapport", () => {
  it("sert un fichier CSV nommé d'après le périmètre et la fenêtre", async () => {
    const response = await call(
      get("/v1/reports/export.csv?scope=farm&scope_id=farm-mboro&from=2026-10-01&to=2026-11-01"),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toContain("text/csv");
    expect(response.headers.get("Content-Disposition")).toBe(
      'attachment; filename="rapport-farm-2026-10-01-2026-11-01.csv"',
    );
    const lines = (await response.text()).trim().split("\n");
    expect(lines[0]).toBe("field_id;nom;surface_ha;culture;kit;eau_m3;from;to");
    expect(lines).toHaveLength(4);
  });

  it("valide le périmètre comme /v1/reports/kpis", async () => {
    expect((await call(get("/v1/reports/export.csv?scope=planete"))).status).toBe(422);
    expect((await call(get("/v1/reports/export.csv?scope=farm&scope_id=farm-mboro"), "farmer")).status).toBe(
      404,
    );
  });
});

describe("pilotage des scénarios", () => {
  afterEach(() => {
    delete process.env.AGRI_MOCK_SCENARIO;
  });

  it("surcharge un service, puis le rend au scénario global", () => {
    setScenario("stale");
    setScenario("empty", "weather");
    expect(scenarioFor("weather")).toBe("empty");
    expect(scenarioFor("vegetation")).toBe("stale");
    expect(snapshot()).toEqual({ global: "stale", overrides: { weather: "empty" } });
    clearScenario("weather");
    expect(scenarioFor("weather")).toBe("stale");
  });

  it("l'instantané est une copie : le modifier ne change pas l'état", () => {
    const copy = snapshot();
    copy.overrides.weather = "error_503";
    expect(scenarioFor("weather")).toBe("nominal");
  });

  it("reconnaît les scénarios et les services valides", () => {
    expect(isScenario("abstention")).toBe(true);
    expect(isScenario("chaos")).toBe(false);
    expect(isScenario(3)).toBe(false);
    expect(isServiceId("map_layers")).toBe(true);
    expect(isServiceId("pricing")).toBe(false);
  });

  it("initialise le scénario global depuis AGRI_MOCK_SCENARIO quand l'état est vide", () => {
    process.env.AGRI_MOCK_SCENARIO = "fallback";
    delete (globalThis as unknown as Record<symbol, unknown>)[Symbol.for("smartagri92.mock.scenario")];
    expect(scenarioFor("weather")).toBe("fallback");
    process.env.AGRI_MOCK_SCENARIO = "inconnu";
    delete (globalThis as unknown as Record<symbol, unknown>)[Symbol.for("smartagri92.mock.scenario")];
    expect(scenarioFor("weather")).toBe("nominal");
  });
});

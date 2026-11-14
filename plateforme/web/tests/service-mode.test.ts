/**
 * Mode hybride par service (Sprint D1) : grammaire d'AGRI_SERVICES, rattachement route → service
 * d'après le registre, et choix simulation / API réelle du BFF (lib/server/upstream.ts).
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { SERVICES, SERVICE_IDS } from "@/lib/contracts/registry";
import { MOCK_BASE } from "@/lib/mock-config";
import {
  DEMO_SLUG_BY_UUID,
  DEMO_UUID_BY_SLUG,
  ServiceModeError,
  allServiceModes,
  modeForPath,
  parseServiceOverrides,
  serviceForPath,
  serviceMode,
  toMockId,
  toRealId,
} from "@/lib/service-mode";
import { deviceSeedById, farmById, fieldSeedById } from "@/mocks/fixtures/places";

vi.mock("server-only", () => ({}));

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

const sample = (template: string): string =>
  (template.split("?")[0] ?? template).replace(/\{[a-z_]+\}/g, "abc-123");

describe("AGRI_SERVICES", () => {
  it("lit nom=mode, espaces et casse tolérés, alias diagnosis_analyze accepté", () => {
    const parsed = parseServiceOverrides(" irrigation_need=real, diagnosis_analyze=REAL ,pest_risk=mock,");
    expect([...parsed]).toEqual([
      ["irrigation_need", "real"],
      ["disease_diagnosis", "real"],
      ["pest_risk", "mock"],
    ]);
    expect(parseServiceOverrides(undefined).size).toBe(0);
    expect(parseServiceOverrides("").size).toBe(0);
  });

  it.each(["irrigation_need", "irrigation_need=maybe", "nope=real", "=real", "irigation_need=real"])(
    "refuse %j",
    (raw) => {
      expect(() => parseServiceOverrides(raw)).toThrow(ServiceModeError);
    },
  );

  it("AGRI_MOCK fixe le défaut, AGRI_SERVICES les exceptions", () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "irrigation_need=real");
    expect(serviceMode("irrigation_need")).toBe("real");
    expect(serviceMode("weather")).toBe("mock");
    vi.stubEnv("AGRI_MOCK", "0");
    vi.stubEnv("AGRI_SERVICES", "pest_risk=mock");
    expect(serviceMode("pest_risk")).toBe("mock");
    expect(serviceMode("weather")).toBe("real");
  });
});

describe("route → service", () => {
  it("rattache irrigation-need au service irrigation_need", () => {
    expect(serviceForPath("/v1/fields/abc/irrigation-need")).toBe("irrigation_need");
    expect(serviceForPath("/v1/fields/abc/irrigation-need/extra")).toBeNull();
  });

  it("chaque route du registre retrouve son service, sans collision", () => {
    for (const def of SERVICES) {
      for (const route of def.routes) {
        expect(serviceForPath(sample(route.path)), `${route.method} ${route.path}`).toBe(def.id);
      }
    }
  });

  it("le registre porte les 18 services de doc 16 §9.3", () => {
    expect(SERVICE_IDS).toHaveLength(18);
  });

  it("une route hors registre suit le défaut global", () => {
    for (const path of ["/v1/auth/login", "/v1/me", "/v1/farms", "/v1/fields/abc"]) {
      expect(serviceForPath(path), path).toBeNull();
    }
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "irrigation_need=real");
    expect(modeForPath("/v1/farms")).toBe("mock");
    expect(modeForPath("/v1/fields/abc/irrigation-need")).toBe("real");
    vi.stubEnv("AGRI_MOCK", "0");
    expect(modeForPath("/v1/farms")).toBe("real");
  });
});

describe("upstream (BFF)", () => {
  it("AGRI_MOCK=1 sans exception : tout est simulé, comme avant", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "");
    const { upstreamBase } = await import("@/lib/server/upstream");
    expect(upstreamBase("/v1/fields/abc/irrigation-need")).toBe(MOCK_BASE);
    expect(upstreamBase("/v1/farms")).toBe(MOCK_BASE);
    expect(upstreamBase()).toBe(MOCK_BASE);
  });

  it("AGRI_MOCK=0 sans exception : tout est réel, comme avant", async () => {
    vi.stubEnv("AGRI_MOCK", "0");
    vi.stubEnv("AGRI_SERVICES", "");
    vi.stubEnv("API_BASE_URL", "http://api.internal:8000/");
    const { upstreamBase } = await import("@/lib/server/upstream");
    expect(upstreamBase("/v1/fields/abc/irrigation-need")).toBe("http://api.internal:8000");
    expect(upstreamBase()).toBe("http://api.internal:8000");
  });

  it("irrigation_need=real : seul ce service part vers l'API, le reste reste simulé", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "irrigation_need=real");
    vi.stubEnv("API_BASE_URL", "http://api.internal:8000");
    const { upstreamBase } = await import("@/lib/server/upstream");
    expect(upstreamBase("/v1/fields/abc/irrigation-need")).toBe("http://api.internal:8000");
    expect(upstreamBase("/v1/fields/abc/weather")).toBe(MOCK_BASE);
    expect(upstreamBase("/v1/fields/abc/pest-risk")).toBe(MOCK_BASE);
    expect(upstreamBase("/v1/auth/login")).toBe(MOCK_BASE);
  });

  it("inversement, AGRI_MOCK=0 et pest_risk=mock : une seule route simulée", async () => {
    vi.stubEnv("AGRI_MOCK", "0");
    vi.stubEnv("AGRI_SERVICES", "pest_risk=mock");
    vi.stubEnv("API_BASE_URL", "http://api.internal:8000");
    const { upstreamBase } = await import("@/lib/server/upstream");
    expect(upstreamBase("/v1/fields/abc/pest-risk")).toBe(MOCK_BASE);
    expect(upstreamBase("/v1/fields/abc/irrigation-need")).toBe("http://api.internal:8000");
  });

  it("upstreamFetch : réseau pour une URL réelle, mocks/ pour l'hôte simulé", async () => {
    vi.stubEnv("AGRI_MOCK", "0");
    const network = vi.fn(async () => new Response("réel", { status: 200 }));
    vi.stubGlobal("fetch", network);
    const { upstreamFetch } = await import("@/lib/server/upstream");
    await upstreamFetch("http://api.internal:8000/v1/me", { method: "GET" });
    expect(network).toHaveBeenCalledTimes(1);
    const simulated = await upstreamFetch(`${MOCK_BASE}/v1/inconnue`, { method: "GET" });
    expect(simulated.status).toBe(404); // route non simulée : réponse de mocks/, jamais le réseau
    expect(network).toHaveBeenCalledTimes(1);
  });

  it("une AGRI_SERVICES invalide fait échouer la résolution au lieu d'être ignorée", async () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "irigation_need=real");
    const { upstreamBase } = await import("@/lib/server/upstream");
    expect(() => upstreamBase("/v1/fields/abc/irrigation-need")).toThrow(ServiceModeError);
  });
});

describe("correspondance déterministe d'identifiants hybrides (Sprint D2)", () => {
  it("mappe chaque slug démo vers un UUID v4 canonique et inversement", () => {
    expect(toRealId("fld-mboro-1")).toBe("00000000-0000-4000-8000-000000000201");
    expect(toRealId("dev-0001")).toBe("00000000-0000-4000-8000-000000000301");
    expect(toMockId("00000000-0000-4000-8000-000000000201")).toBe("fld-mboro-1");
    expect(toMockId("00000000-0000-4000-8000-000000000301")).toBe("dev-0001");
    for (const [slug, uuid] of Object.entries(DEMO_UUID_BY_SLUG)) {
      expect(DEMO_SLUG_BY_UUID[uuid]).toBe(slug);
    }
  });

  it("résout les graines mock aussi bien par slug que par UUID canonique, sans masquer un 404 inconnu", () => {
    expect(fieldSeedById("fld-mboro-1")?.id).toBe("fld-mboro-1");
    expect(fieldSeedById("00000000-0000-4000-8000-000000000201")?.id).toBe("fld-mboro-1");
    expect(deviceSeedById("00000000-0000-4000-8000-000000000301")?.id).toBe("dev-0001");
    expect(farmById("00000000-0000-4000-8000-000000000101")?.id).toBe("farm-mboro");
    expect(fieldSeedById("00000000-0000-0000-0000-000000000000")).toBeNull();
  });

  it("allServiceModes expose les 18 services avec leurs surcharges effectives", () => {
    vi.stubEnv("AGRI_MOCK", "1");
    vi.stubEnv("AGRI_SERVICES", "weather=real,recommendations=real");
    const modes = allServiceModes();
    expect(Object.keys(modes)).toHaveLength(18);
    expect(modes.weather).toBe("real");
    expect(modes.recommendations).toBe("real");
    expect(modes.pest_risk).toBe("mock");
  });
});

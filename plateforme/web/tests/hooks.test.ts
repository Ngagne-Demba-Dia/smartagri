/**
 * Hooks React Query des 18 services (services/ai) par le client réel du navigateur (lib/client.ts) : c'est le
 * chemin des composants. Sans DOM : rendu serveur (renderToString), puis exécution des requêtes enregistrées
 * dans le cache. fetch est remplacé par les simulations MSW de doc 16 §9.5 ; seul le BFF manque au trajet.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useFarms } from "@/hooks/places";
import { api } from "@/lib/client";
import type { AlertView } from "@/lib/contracts/device";
import { MOCK_BASE } from "@/lib/mock-config";
import { handleMock, resetScenarios, resetStore } from "@/mocks";
import {
  aiKeys,
  useAckAlert,
  useAlerts,
  useChat,
  useDeviceHealth,
  useDiagnosis,
  useFarmMapLayers,
  useFarmMaps,
  useFertilization,
  useIrrigationNeed,
  useIrrigationPlan,
  useKitParameters,
  useKpis,
  usePestRisk,
  usePriceForecast,
  useRecommendationFeedback,
  useRecommendations,
  useSoilForecast,
  useTranscribe,
  useTrapCounts,
  useVegetation,
  useWeather,
  useYieldForecast,
} from "@/services/ai";

import { bearer, diagnosisBody, transcribeBody, type Role } from "./helpers";

process.env.AGRI_MOCK_LATENCY = "0";

const FIELD = "fld-mboro-1";
const FARM = "farm-mboro";
const DEVICE = "dev-0001";
const WINDOW = { from: "2026-10-01", to: "2026-11-01" };
const BFF_PREFIX = "/api";

/** fetch du navigateur → simulations : /api/v1/… devient MOCK_BASE/v1/…, avec le jeton qu'ajouterait le BFF. */
function stubBff(role: Role | null = "admin") {
  const calls: string[] = [];
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    calls.push(`${init?.method ?? "GET"} ${path}`);
    const headers = new Headers(init?.headers);
    if (role) headers.set("authorization", bearer(role).authorization ?? "");
    return handleMock(new Request(`${MOCK_BASE}${path.slice(BFF_PREFIX.length)}`, { ...init, headers }));
  });
  return calls;
}

/**
 * Chaque renderToString est un nouveau montage : `retryOnMount: false` garde l'erreur affichée comme le ferait
 * un composant resté monté, au lieu de la remplacer par un chargement.
 */
function newClient(retryOnMount = true): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, retryOnMount }, mutations: { retry: false } },
  });
}

/** Rendu serveur d'un composant qui appelle `use` ; renvoie la valeur des hooks au dernier rendu. */
function renderHooks<T>(client: QueryClient, use: () => T): T {
  const box: { value?: T } = {};
  const Probe = () => {
    box.value = use();
    return null;
  };
  renderToString(createElement(QueryClientProvider, { client }, createElement(Probe)));
  if (box.value === undefined) throw new Error("Hooks non rendus.");
  return box.value;
}

/** Exécute chaque requête du cache encore sans données (le rendu serveur les enregistre sans les lancer). */
async function settle(client: QueryClient): Promise<void> {
  for (const query of client.getQueryCache().getAll()) {
    if (query.state.data === undefined) await query.fetch();
  }
}

beforeEach(() => {
  resetScenarios();
  resetStore();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const useFieldServices = () => ({
  weather: useWeather(FIELD),
  soil: useSoilForecast(FIELD),
  need: useIrrigationNeed(FIELD),
  plan: useIrrigationPlan(FARM, "2026-11-12"),
  recommendations: useRecommendations(FIELD),
  fertilization: useFertilization(FIELD),
  parameters: useKitParameters(DEVICE),
  pests: usePestRisk(FIELD),
  traps: useTrapCounts(DEVICE, WINDOW.from, WINDOW.to),
  vegetation: useVegetation(FIELD, WINDOW.from, WINDOW.to),
  yieldForecast: useYieldForecast(FIELD),
  health: useDeviceHealth(DEVICE),
  alerts: useAlerts(),
  allAlerts: useAlerts("all"),
  kpis: useKpis(WINDOW),
  prices: usePriceForecast("oignon", "Thiaroye"),
});

describe("hooks de lecture", () => {
  it("chaque hook enregistre sa requête ; exécutée, elle passe par le BFF et valide le contrat", async () => {
    const calls = stubBff();
    const client = newClient();
    const first = renderHooks(client, useFieldServices);
    expect(Object.values(first).every((q) => q.isPending)).toBe(true);
    expect(calls).toEqual([]);

    await settle(client);
    const queries = client.getQueryCache().getAll();
    expect(queries).toHaveLength(16);
    expect(queries.filter((q) => q.state.status !== "success").map((q) => q.queryKey)).toEqual([]);
    expect(calls.every((c) => c.startsWith("GET /api/v1/"))).toBe(true);
    expect(calls).toContain(`GET /api/v1/fields/${FIELD}/weather?days=7`);

    const second = renderHooks(client, useFieldServices);
    expect(second.weather.data?.provenance?.model_name.length).toBeGreaterThan(0);
    expect(second.kpis.data?.kpis.water_savings).not.toBeNull();
  });

  it("sans identifiant : requêtes inactives, aucune requête réseau", () => {
    const calls = stubBff();
    const client = newClient();
    const result = renderHooks(client, () => [
      useWeather(null),
      useSoilForecast(null),
      useIrrigationNeed(null),
      useIrrigationPlan(null, "2026-11-12"),
      useRecommendations(null),
      useFertilization(null),
      useKitParameters(null),
      usePestRisk(null),
      useTrapCounts(null, WINDOW.from, WINDOW.to),
      useVegetation(null, WINDOW.from, WINDOW.to),
      useYieldForecast(null),
      useDeviceHealth(null),
      usePriceForecast(null, "Thiaroye"),
      useFarmMapLayers(null, ["crop_type"]),
      useFarmMapLayers(FARM, []),
    ]);
    expect(result.every((q) => q.fetchStatus === "idle" && q.data === undefined)).toBe(true);
    expect(calls).toEqual([]);
  });
});

describe("cartes des exploitations (service 18)", () => {
  it("useFarmMaps attend les exploitations puis combine une carte par exploitation", async () => {
    stubBff();
    const client = newClient();
    const use = () => ({ maps: useFarmMaps(), layers: useFarmMapLayers(FARM, ["crop_type"]) });

    expect(renderHooks(client, use).maps).toMatchObject({
      farms: [],
      maps: [],
      isPending: true,
      error: null,
    });
    await settle(client); // exploitations et couche demandée
    const withFarms = renderHooks(client, use);
    expect(withFarms.maps.farms.length).toBeGreaterThan(0);
    expect(withFarms.maps.isPending).toBe(true);

    await settle(client); // une carte par exploitation
    const done = renderHooks(client, use);
    expect(done.maps.isPending).toBe(false);
    expect(done.maps.maps.map((m) => m.farmId)).toEqual(done.maps.farms.map((f) => f.id));
    expect(done.maps.dataUpdatedAt).toBeGreaterThan(0);
    expect(done.layers.data?.features.length).toBeGreaterThan(0);
  });

  it("refetch relance les exploitations et chaque carte", async () => {
    const calls = stubBff();
    const client = newClient();
    renderHooks(client, () => useFarmMaps());
    await settle(client);
    renderHooks(client, () => useFarmMaps());
    await settle(client);
    const before = calls.length;

    renderHooks(client, () => useFarmMaps()).refetch();
    await vi.waitFor(() => expect(client.isFetching()).toBe(0));
    expect(calls.length - before).toBe(before);
  });

  it("une erreur de la liste des exploitations remonte dans le résultat combiné", async () => {
    stubBff(null);
    const client = newClient(false);
    renderHooks(client, () => useFarmMaps());
    await settle(client).catch(() => undefined);
    const result = renderHooks(client, () => useFarmMaps());
    expect(result.isPending).toBe(false);
    expect(result.error).toMatchObject({ status: 401 });
  });
});

describe("hooks d'action", () => {
  it("assistant, transcription et diagnostic renvoient le contrat", async () => {
    stubBff();
    const client = newClient();
    const hooks = renderHooks(client, () => ({
      chat: useChat(),
      transcribe: useTranscribe(),
      diagnosis: useDiagnosis(),
    }));

    const reply = await hooks.chat.mutateAsync({ message: "Quand arroser mes oignons ?" });
    const text = await hooks.transcribe.mutateAsync(transcribeBody("wo"));
    const verdict = await hooks.diagnosis.mutateAsync(diagnosisBody());
    expect(reply.reply.length).toBeGreaterThan(0);
    expect(text.language).toBe("wo");
    expect(verdict.provenance.model_name.length).toBeGreaterThan(0);
  });

  it("acquitter une alerte invalide les listes d'alertes et les exploitations", async () => {
    const calls = stubBff();
    const client = newClient();
    renderHooks(client, () => ({ alerts: useAlerts(), farms: useFarms() }));
    await settle(client);
    const first = client.getQueryData<AlertView[]>(aiKeys.alerts("open"))?.[0];
    if (!first) throw new Error("Aucune alerte ouverte simulée.");

    const ack = renderHooks(client, () => useAckAlert());
    const acknowledged = await ack.mutateAsync(first.id);
    expect(acknowledged.status).toBe("acknowledged");
    expect(calls).toContain(`POST /api/v1/alerts/${first.id}/ack`);
    const invalidated = client
      .getQueryCache()
      .getAll()
      .filter((q) => q.state.isInvalidated);
    expect(invalidated.map((q) => q.queryKey[0]).sort()).toEqual(["alerts", "farms"]);
  });

  it("retour sur une recommandation", async () => {
    stubBff();
    const client = newClient();
    const feedback = renderHooks(client, () => useRecommendationFeedback());
    const reco = await feedback.mutateAsync({ id: "rec-fld-mboro-1-irr", feedback: "followed" });
    expect(reco.id).toBe("rec-fld-mboro-1-irr");
  });
});

describe("client du navigateur (lib/client.ts)", () => {
  it("session expirée : un seul rafraîchissement, puis renvoi vers la connexion avec la page en cours", async () => {
    const calls = stubBff(null);
    const assign = vi.fn();
    vi.stubGlobal("window", { location: { pathname: "/wo/carte", search: "?mode=ndvi", assign } });

    await expect(api.get("/v1/farms")).rejects.toMatchObject({ status: 401 });
    expect(calls).toEqual(["GET /api/v1/farms", "POST /api/auth/refresh"]);
    expect(assign).toHaveBeenCalledWith("/wo/login?next=%2Fcarte%3Fmode%3Dndvi");
  });

  it("pas de renvoi depuis la page de connexion ni hors navigateur", async () => {
    stubBff(null);
    const assign = vi.fn();
    vi.stubGlobal("window", { location: { pathname: "/fr/login", search: "", assign } });
    await expect(api.get("/v1/farms")).rejects.toMatchObject({ status: 401 });
    expect(assign).not.toHaveBeenCalled();

    vi.unstubAllGlobals();
    stubBff(null);
    await expect(api.get("/v1/farms")).rejects.toMatchObject({ status: 401 });
  });
});

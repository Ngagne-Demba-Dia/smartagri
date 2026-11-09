import { describe, expect, it } from "vitest";

import { campaignProgress, daysLeft, sortedCampaigns } from "@/lib/campaigns";
import { countByStatus, cycleSteps, filterCycles, sortedCycles } from "@/lib/crop-cycles";
import { sortedEquipment, summarizeEquipment } from "@/lib/equipment";
import type { Campaign, CropCycle, Equipment } from "@/lib/types";

const cycle = (over: Partial<CropCycle> = {}): CropCycle => ({
  id: "c1",
  organization_id: "o1",
  field_id: "f1",
  campaign_id: null,
  crop: "oignon",
  variety: null,
  planted_on: "2027-01-10",
  expected_harvest_on: "2027-05-01",
  harvested_on: null,
  yield_kg: null,
  status: "active",
  created_at: "2027-01-01T00:00:00Z",
  ...over,
});

const campaign = (over: Partial<Campaign> = {}): Campaign => ({
  id: "k1",
  organization_id: "o1",
  name: "Contre-saison 2027",
  season: "2027",
  start_date: "2027-01-01",
  end_date: "2027-01-11",
  status: "active",
  created_at: "2026-12-01T00:00:00Z",
  ...over,
});

const item = (over: Partial<Equipment> = {}): Equipment => ({
  id: "e1",
  organization_id: "o1",
  farm_id: "farm-1",
  kind: "pump",
  label: "Pompe",
  serial: null,
  installed_at: null,
  status: "ok",
  device_id: null,
  flow_m3h: null,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
});

describe("cycleSteps", () => {
  const states = (c: CropCycle) => cycleSteps(c).map((s) => s.state);

  it("cycle prévu : le semis est l'étape en cours", () => {
    expect(states(cycle({ status: "planned", planted_on: null }))).toEqual(["current", "todo", "todo"]);
  });

  it("cycle actif : semis fait, croissance en cours", () => {
    expect(states(cycle())).toEqual(["done", "current", "todo"]);
  });

  it("cycle récolté : tout est fait et la date de récolte réelle l'emporte", () => {
    const steps = cycleSteps(cycle({ status: "harvested", harvested_on: "2027-04-20" }));
    expect(steps.map((s) => s.state)).toEqual(["done", "done", "done"]);
    expect(steps[2]?.date).toBe("2027-04-20");
  });

  it("cycle abandonné : le semis reste fait, rien n'est en cours", () => {
    expect(states(cycle({ status: "abandoned" }))).toEqual(["done", "todo", "todo"]);
  });

  it("date de récolte prévue tant que rien n'est récolté", () => {
    expect(cycleSteps(cycle())[2]?.date).toBe("2027-05-01");
  });
});

describe("cycles : filtre, tri, comptage", () => {
  const list = [
    cycle({ id: "a", status: "harvested", planted_on: "2026-06-01" }),
    cycle({ id: "b", status: "active", planted_on: "2027-01-10" }),
    cycle({ id: "c", status: "active", planted_on: "2027-02-10" }),
    cycle({ id: "d", status: "planned", planted_on: null, created_at: "2027-03-01T00:00:00Z" }),
  ];

  it("filtre par statut, « all » garde tout", () => {
    expect(filterCycles(list, "active").map((c) => c.id)).toEqual(["b", "c"]);
    expect(filterCycles(list, "all")).toHaveLength(4);
  });

  it("trie les cycles en cours d'abord, le plus récent en tête, sans muter l'entrée", () => {
    const before = list.map((c) => c.id);
    expect(sortedCycles(list).map((c) => c.id)).toEqual(["c", "b", "d", "a"]);
    expect(list.map((c) => c.id)).toEqual(before);
  });

  it("compte par statut", () => {
    expect(countByStatus(list)).toEqual({ all: 4, active: 2, planned: 1, harvested: 1, abandoned: 0 });
  });
});

describe("campagnes", () => {
  const now = new Date("2027-01-06T00:00:00Z");

  it("avancement d'une campagne en cours situé par les dates", () => {
    expect(campaignProgress(campaign(), now)).toBe(50);
  });

  it("prévue = 0, close = 100, hors bornes ramené à 0..100", () => {
    expect(campaignProgress(campaign({ status: "planned" }), now)).toBe(0);
    expect(campaignProgress(campaign({ status: "closed" }), now)).toBe(100);
    expect(campaignProgress(campaign(), new Date("2026-12-01T00:00:00Z"))).toBe(0);
    expect(campaignProgress(campaign(), new Date("2027-06-01T00:00:00Z"))).toBe(100);
  });

  it("dates illisibles ou inversées : pas d'avancement inventé", () => {
    expect(campaignProgress(campaign({ end_date: "n/a" }), now)).toBeNull();
    expect(campaignProgress(campaign({ end_date: "2026-12-01" }), now)).toBeNull();
  });

  it("jours restants : seulement pour une campagne en cours, jamais négatifs", () => {
    expect(daysLeft(campaign(), now)).toBe(5);
    expect(daysLeft(campaign(), new Date("2027-03-01T00:00:00Z"))).toBe(0);
    expect(daysLeft(campaign({ status: "closed" }), now)).toBeNull();
    expect(daysLeft(campaign({ end_date: "n/a" }), now)).toBeNull();
  });

  it("tri : en cours, prévues, puis closes", () => {
    const list = [
      campaign({ id: "x", status: "closed", start_date: "2026-01-01" }),
      campaign({ id: "y", status: "planned", start_date: "2027-06-01" }),
      campaign({ id: "z", status: "active", start_date: "2027-01-01" }),
    ];
    expect(sortedCampaigns(list).map((c) => c.id)).toEqual(["z", "y", "x"]);
  });
});

describe("équipements", () => {
  const list = [
    item({ id: "1", label: "Réservoir", status: "ok" }),
    item({ id: "2", label: "Pompe nord", status: "out_of_service" }),
    item({ id: "3", label: "Capteur", status: "maintenance" }),
    item({ id: "4", label: "Batterie", status: "ok" }),
  ];

  it("synthèse par état", () => {
    expect(summarizeEquipment(list)).toEqual({ total: 4, ok: 2, maintenance: 1, out_of_service: 1 });
    expect(summarizeEquipment([])).toEqual({ total: 0, ok: 0, maintenance: 0, out_of_service: 0 });
  });

  it("met ce qui demande une action en premier, puis l'ordre alphabétique", () => {
    expect(sortedEquipment(list).map((e) => e.label)).toEqual([
      "Pompe nord",
      "Capteur",
      "Batterie",
      "Réservoir",
    ]);
  });
});

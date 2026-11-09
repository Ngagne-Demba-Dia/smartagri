// @vitest-environment jsdom
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CampaignsView } from "@/features/campaigns/CampaignsView";
import { CropsView } from "@/features/crops/CropsView";
import { EquipmentView } from "@/features/equipment/EquipmentView";
import { YieldView } from "@/features/yield/YieldView";

import { makeProvenance, renderFr } from "./render";

type Query = { isPending: boolean; error: Error | null; data: unknown; refetch: () => Promise<unknown> };

const mocks = vi.hoisted(() => ({
  cycles: vi.fn(),
  campaigns: vi.fn(),
  equipment: vi.fn(),
  yieldForecast: vi.fn(),
  allFields: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/fr/cultures",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/components/chart/Chart", () => ({
  Chart: ({ title, spec }: { title: string; spec: { summary: string } }) => (
    <figure aria-label={title}>{spec.summary}</figure>
  ),
}));
vi.mock("@/features/kit/KitHealthSection", () => ({
  KitHealthSection: () => <section>Santé des kits</section>,
}));
vi.mock("@/hooks/field-data", () => ({ useCropCycles: mocks.cycles }));
vi.mock("@/hooks/reports", () => ({ useCampaigns: mocks.campaigns, useEquipment: mocks.equipment }));
vi.mock("@/hooks/places", () => ({ useAllFields: mocks.allFields }));
vi.mock("@/services/ai/yield-forecast", () => ({ useYieldForecast: mocks.yieldForecast }));

const ok = (data: unknown): Query => ({ isPending: false, error: null, data, refetch: vi.fn() });
const pending = (): Query => ({ isPending: true, error: null, data: undefined, refetch: vi.fn() });

const FARM = { id: "farm-1", name: "Ferme des Niayes" };
const FIELD = { id: "field-1", name: "Parcelle Nord", farm_id: "farm-1" };

const cycle = (over: Record<string, unknown> = {}) => ({
  id: "c1",
  organization_id: "o1",
  field_id: "field-1",
  campaign_id: null,
  crop: "oignon",
  variety: "Violet de Galmi",
  planted_on: "2027-01-10",
  expected_harvest_on: "2027-05-01",
  harvested_on: null,
  yield_kg: null,
  status: "active",
  created_at: "2027-01-01T00:00:00Z",
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
  mocks.allFields.mockReturnValue({
    fields: [FIELD],
    farms: [FARM],
    isPending: false,
    error: null,
    refetch: vi.fn(),
  });
});

describe("Cultures (module 6)", () => {
  it("montre les étapes du cycle et la culture avec sa variété", () => {
    mocks.cycles.mockReturnValue(ok([cycle()]));
    renderFr(<CropsView initialFieldId="field-1" />);
    expect(screen.getByRole("heading", { level: 1, name: "Cultures" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "oignon (Violet de Galmi)" })).toBeInTheDocument();
    const steps = screen.getByRole("list", { name: "Étapes du cycle oignon" });
    expect(within(steps).getByText("Croissance")).toBeInTheDocument();
    expect(within(steps).getByText(/prévue le/)).toBeInTheDocument();
  });

  it("filtre par statut et signale un filtre sans résultat", async () => {
    mocks.cycles.mockReturnValue(ok([cycle(), cycle({ id: "c2", status: "harvested", yield_kg: 1200 })]));
    renderFr(<CropsView initialFieldId="field-1" />);
    expect(screen.getByRole("radio", { name: "En cours (1)" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Récoltés (1)" }));
    expect(screen.getByText(/Rendement récolté : 1\s?200 kg/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Abandonnés (0)" }));
    expect(screen.getByText("Aucun cycle dans cet état.")).toBeInTheDocument();
  });

  it("n'invente pas de rendement pour un cycle récolté sans valeur", async () => {
    mocks.cycles.mockReturnValue(ok([cycle({ status: "harvested", harvested_on: "2027-04-20" })]));
    renderFr(<CropsView initialFieldId="field-1" />);
    await userEvent.click(screen.getByRole("radio", { name: "Récoltés (1)" }));
    expect(screen.getByText("Rendement non communiqué")).toBeInTheDocument();
  });

  it("dit qu'il n'y a pas de cycle, ou pas de parcelle", () => {
    mocks.cycles.mockReturnValue(ok([]));
    renderFr(<CropsView initialFieldId="field-1" />);
    expect(screen.getByText("Aucun cycle de culture pour cette parcelle.")).toBeInTheDocument();
  });

  it("affiche un état de chargement sans liste", () => {
    mocks.cycles.mockReturnValue(pending());
    renderFr(<CropsView initialFieldId="field-1" />);
    expect(screen.queryByRole("list", { name: "Cycles de culture" })).not.toBeInTheDocument();
  });
});

describe("Campagnes (module 11)", () => {
  const campaign = (over: Record<string, unknown> = {}) => ({
    id: "k1",
    organization_id: "o1",
    name: "Contre-saison",
    season: "2027",
    start_date: "2020-01-01",
    end_date: "2099-01-01",
    status: "active",
    created_at: "2019-12-01T00:00:00Z",
    ...over,
  });

  it("montre une jauge d'avancement pour une campagne en cours", () => {
    mocks.campaigns.mockReturnValue(ok([campaign()]));
    renderFr(<CampaignsView />);
    expect(
      screen.getByRole("meter", { name: "Avancement de la campagne Contre-saison" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/jours restants/)).toBeInTheDocument();
  });

  it("annonce le début d'une campagne prévue, sans jauge", () => {
    mocks.campaigns.mockReturnValue(ok([campaign({ status: "planned", start_date: "2099-02-01" })]));
    renderFr(<CampaignsView />);
    expect(screen.getByText(/Commence le/)).toBeInTheDocument();
    expect(screen.queryByRole("meter")).not.toBeInTheDocument();
  });

  it("ne calcule pas l'avancement quand les dates sont illisibles", () => {
    mocks.campaigns.mockReturnValue(ok([campaign({ end_date: "n/a" })]));
    renderFr(<CampaignsView />);
    expect(screen.getByText(/l’avancement n’est pas calculé/)).toBeInTheDocument();
  });

  it("état vide", () => {
    mocks.campaigns.mockReturnValue(ok([]));
    renderFr(<CampaignsView />);
    expect(screen.getByText("Aucune campagne pour le moment.")).toBeInTheDocument();
  });
});

describe("Rendement (module 9)", () => {
  const view = (over: Record<string, unknown> = {}) => ({
    field_id: "field-1",
    crop_cycle: { id: "c1", crop: "oignon", status: "active", planted_on: "2027-01-10" },
    forecast: {
      id: "fc1",
      model_name: "yield_gbm",
      model_version: "0.3",
      predicted_t_ha: 24.5,
      p10: 19,
      p90: 29,
      created_at: "2027-03-01T00:00:00Z",
    },
    actual_t_ha: null,
    caveat: "Modèle expérimental : à confirmer avec votre technicien.",
    provenance: makeProvenance(),
    ...over,
  });

  it("présente le rendement prévu, l'intervalle et la mise en garde", () => {
    mocks.yieldForecast.mockReturnValue(ok(view()));
    renderFr(<YieldView initialFieldId="field-1" />);
    expect(screen.getByText("Expérimental")).toBeInTheDocument();
    expect(screen.getByText("24,5 t/ha")).toBeInTheDocument();
    expect(screen.getByText("19 t/ha à 29 t/ha")).toBeInTheDocument();
    expect(screen.getByText("Pas encore récolté")).toBeInTheDocument();
    expect(screen.getByText(/Modèle expérimental/)).toBeInTheDocument();
    expect(screen.getByLabelText("Rendement prévu et intervalle probable")).toBeInTheDocument();
  });

  it("dit qu'il n'y a pas encore de prévision", () => {
    mocks.yieldForecast.mockReturnValue(ok(view({ forecast: null })));
    renderFr(<YieldView initialFieldId="field-1" />);
    expect(screen.getByText("Pas encore de prévision pour ce cycle.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Rendement prévu et intervalle probable")).not.toBeInTheDocument();
  });

  it("dit que la provenance n'est pas communiquée plutôt que de la supposer", async () => {
    mocks.yieldForecast.mockReturnValue(ok(view({ provenance: null })));
    renderFr(<YieldView initialFieldId="field-1" />);
    expect(screen.queryByText("À jour")).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Provenance"));
    expect(screen.getByText(/Provenance non communiquée/)).toBeInTheDocument();
  });
});

describe("Équipements (module 10)", () => {
  const item = (over: Record<string, unknown> = {}) => ({
    id: "e1",
    organization_id: "o1",
    farm_id: "farm-1",
    kind: "pump",
    label: "Pompe nord",
    serial: "P-001",
    installed_at: "2026-05-01",
    status: "ok",
    device_id: null,
    flow_m3h: 12.5,
    created_at: "2026-05-01T00:00:00Z",
    ...over,
  });

  it("résume l'état du parc et signale ce qui demande une intervention", () => {
    mocks.equipment.mockReturnValue(
      ok([
        item(),
        item({ id: "e2", label: "Capteur", kind: "sensor", status: "out_of_service", flow_m3h: null }),
      ]),
    );
    renderFr(<EquipmentView />);
    expect(screen.getByRole("status")).toHaveTextContent("1 équipement demande une intervention.");
    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(within(rows[1]!).getByText("Hors service")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voir l’état des kits" })).toHaveAttribute("href", "/fr/kit");
    expect(screen.getByText("Santé des kits")).toBeInTheDocument();
  });

  it("tout en service", () => {
    mocks.equipment.mockReturnValue(ok([item()]));
    renderFr(<EquipmentView />);
    expect(screen.getByRole("status")).toHaveTextContent("Tous les équipements sont en service.");
  });

  it("état vide", () => {
    mocks.equipment.mockReturnValue(ok([]));
    renderFr(<EquipmentView />);
    expect(screen.getByText("Aucun équipement enregistré.")).toBeInTheDocument();
  });
});

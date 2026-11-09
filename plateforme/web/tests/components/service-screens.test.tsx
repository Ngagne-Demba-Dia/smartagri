// @vitest-environment jsdom
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { IrrigationPlanView } from "@/features/irrigation-plan/IrrigationPlanView";
import { MarketsView } from "@/features/markets/MarketsView";
import { SoilForecastView } from "@/features/soil-forecast/SoilForecastView";
import { TrapsView } from "@/features/traps/TrapsView";
import { VegetationView } from "@/features/vegetation/VegetationView";

import { makeProvenance, renderFr } from "./render";

type Query = { isPending: boolean; error: Error | null; data: unknown; refetch: () => Promise<unknown> };

const mocks = vi.hoisted(() => ({
  soil: vi.fn(),
  plan: vi.fn(),
  traps: vi.fn(),
  vegetation: vi.fn(),
  prices: vi.fn(),
  devices: vi.fn(),
  farms: vi.fn(),
  allFields: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/fr/previsions",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/components/chart/Chart", () => ({
  Chart: ({ title, spec }: { title: string; spec: { summary: string } }) => (
    <figure aria-label={title}>{spec.summary}</figure>
  ),
}));
vi.mock("@/services/ai/soil-forecast", () => ({ useSoilForecast: mocks.soil }));
vi.mock("@/services/ai/irrigation-plan", () => ({ useIrrigationPlan: mocks.plan }));
vi.mock("@/services/ai/trap-counts", () => ({ useTrapCounts: mocks.traps }));
vi.mock("@/services/ai/vegetation", () => ({ useVegetation: mocks.vegetation }));
vi.mock("@/services/ai/price-forecast", () => ({ usePriceForecast: mocks.prices }));
vi.mock("@/hooks/devices", () => ({ useDevices: mocks.devices }));
vi.mock("@/hooks/places", () => ({ useFarms: mocks.farms, useAllFields: mocks.allFields }));

const ok = (data: unknown): Query => ({ isPending: false, error: null, data, refetch: vi.fn() });
const pending = (): Query => ({ isPending: true, error: null, data: undefined, refetch: vi.fn() });

const FARM = { id: "farm-1", name: "Ferme des Niayes" };
const FIELD = { id: "field-1", name: "Parcelle Nord", farm_id: "farm-1" };
const DEVICE = { id: "dev-1", serial: "SA-001", name: "Kit Nord", field_id: "field-1", status: "active" };

beforeEach(() => {
  vi.clearAllMocks();
  mocks.farms.mockReturnValue(ok([FARM]));
  mocks.allFields.mockReturnValue({
    fields: [FIELD],
    farms: [FARM],
    isPending: false,
    error: null,
    refetch: vi.fn(),
  });
  mocks.devices.mockReturnValue(ok([DEVICE]));
});

describe("Humidité prévue (service 2)", () => {
  const forecast = (thresholds: { start_pct: number; stop_pct: number } | null) => ({
    field_id: "field-1",
    device_id: "dev-1",
    issued_at: "2027-03-02T06:00:00Z",
    thresholds,
    horizons: [
      { hours: 24, p10: 30, p50: 34, p90: 38 },
      { hours: 48, p10: 22, p50: 28, p90: 33 },
      { hours: 72, p10: 18, p50: 22, p90: 27 },
    ],
    provenance: makeProvenance(),
  });

  it("annonce le premier passage sous le seuil de démarrage", () => {
    mocks.soil.mockReturnValue(ok(forecast({ start_pct: 25, stop_pct: 35 })));
    renderFr(<SoilForecastView initialFieldId="field-1" />);
    expect(screen.getByRole("heading", { level: 1, name: "Humidité prévue" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("passe sous le seuil de démarrage");
    expect(screen.getByText("Sous le seuil de démarrage")).toBeInTheDocument();
  });

  it("dit que les seuils manquent plutôt que de les inventer", () => {
    mocks.soil.mockReturnValue(ok(forecast(null)));
    renderFr(<SoilForecastView initialFieldId="field-1" />);
    expect(screen.getByText(/seuils du kit ne sont pas communiqués/)).toBeInTheDocument();
  });

  it("explique l'absence de kit quand aucun horizon n'est prévu", () => {
    mocks.soil.mockReturnValue(ok({ ...forecast(null), horizons: [] }));
    renderFr(<SoilForecastView initialFieldId="field-1" />);
    expect(screen.getByText(/n’a pas de kit installé/)).toBeInTheDocument();
  });
});

describe("Planning d'arrosage (service 4)", () => {
  it("liste les créneaux avec le nom de la parcelle et les totaux", () => {
    mocks.plan.mockReturnValue(
      ok({
        farm_id: "farm-1",
        date: "2027-03-02",
        slots: [
          {
            field_id: "field-1",
            pump_id: "pump-1",
            start: "2027-03-02T06:00:00Z",
            end: "2027-03-02T06:45:00Z",
            volume_m3: 12.5,
          },
          {
            field_id: "field-9",
            pump_id: "pump-1",
            start: "2027-03-02T07:00:00Z",
            end: "2027-03-02T08:00:00Z",
            volume_m3: 20,
          },
        ],
        provenance: makeProvenance(),
      }),
    );
    renderFr(<IrrigationPlanView />);
    const table = screen.getByRole("table");
    expect(within(table).getByText("Parcelle Nord")).toBeInTheDocument();
    expect(within(table).getByText("Parcelle field-9")).toBeInTheDocument();
    expect(screen.getByText(/Proposition à confirmer/)).toBeInTheDocument();
    expect(screen.getByText("Parcelles concernées")).toBeInTheDocument();
  });

  it("bascule sur demain sans plantage", async () => {
    mocks.plan.mockReturnValue(
      ok({ farm_id: "farm-1", date: "2027-03-03", slots: [], provenance: makeProvenance() }),
    );
    renderFr(<IrrigationPlanView />);
    await userEvent.click(screen.getByRole("radio", { name: "Demain" }));
    expect(screen.getByText("Aucun créneau proposé pour ce jour.")).toBeInTheDocument();
  });

  it("affiche l'état de chargement des exploitations", () => {
    mocks.farms.mockReturnValue(pending());
    mocks.plan.mockReturnValue(pending());
    renderFr(<IrrigationPlanView />);
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("Pièges à insectes (service 10)", () => {
  it("résume les captures par jour", () => {
    mocks.traps.mockReturnValue(
      ok({
        device_id: "dev-1",
        from: "2027-02-16T00:00:00Z",
        to: "2027-03-02T00:00:00Z",
        pest_code: "inconnu",
        series: [
          { captured_at: "2027-03-01T08:00:00Z", count: 4, image_id: "img-1" },
          { captured_at: "2027-03-01T16:00:00Z", count: 2, image_id: null },
          { captured_at: "2027-03-02T08:00:00Z", count: 6, image_id: "img-2" },
        ],
        provenance: makeProvenance(),
      }),
    );
    renderFr(<TrapsView initialDeviceId="dev-1" />);
    expect(screen.getByText("Organisme compté : inconnu")).toBeInTheDocument();
    expect(screen.getByText("Trop peu de jours")).toBeInTheDocument();
    expect(screen.getByLabelText("Captures par jour")).toHaveTextContent("2 jours, 12 au total");
    expect(screen.getByText(/à vérifier sur le piège/)).toBeInTheDocument();
  });

  it("signale l'absence de kit actif", () => {
    mocks.devices.mockReturnValue(ok([]));
    renderFr(<TrapsView initialDeviceId={null} />);
    expect(screen.getByText("Aucun kit actif.")).toBeInTheDocument();
  });
});

describe("Végétation (service 11)", () => {
  const data = (gapfilled: boolean) => ({
    field_id: "field-1",
    from: "2027-01-01",
    to: "2027-03-01",
    series: [
      { date: "2027-02-01", ndvi: 0.5, evi: 0.3, gapfilled: false },
      { date: "2027-02-15", ndvi: 0.62, evi: 0.35, gapfilled },
    ],
    stage: { bbch: 31, label: "Montaison" },
    canopy_cover_pct: 54,
    provenance: makeProvenance(),
  });

  it("montre la dernière valeur, la variation et le stade", () => {
    mocks.vegetation.mockReturnValue(ok(data(true)));
    renderFr(<VegetationView initialFieldId="field-1" />);
    expect(screen.getByText("0,62")).toBeInTheDocument();
    expect(screen.getByText("Montaison")).toBeInTheDocument();
    expect(screen.getByText("Code BBCH 31")).toBeInTheDocument();
    expect(screen.getByText(/sont reconstitués/)).toBeInTheDocument();
  });

  it("ne parle pas de reconstitution quand tout est mesuré", () => {
    mocks.vegetation.mockReturnValue(ok(data(false)));
    renderFr(<VegetationView initialFieldId="field-1" />);
    expect(screen.queryByText(/sont reconstitués/)).not.toBeInTheDocument();
  });

  it("dit que le stade n'est pas communiqué", () => {
    mocks.vegetation.mockReturnValue(ok({ ...data(false), stage: null }));
    renderFr(<VegetationView initialFieldId="field-1" />);
    expect(screen.getByText("Stade non communiqué")).toBeInTheDocument();
  });
});

describe("Prix du marché (service 15)", () => {
  const prices = (observed: { date: string; price: number } | null) => ({
    crop: "oignon",
    market: "thiaroye",
    currency: "XOF",
    unit: "kg",
    observed,
    horizons: [
      { weeks: 1, p10: 280, p50: 300, p90: 330 },
      { weeks: 2, p10: 270, p50: 330, p90: 380 },
    ],
    provenance: makeProvenance(),
  });

  it("chiffre l'écart à la dernière observation", () => {
    mocks.prices.mockReturnValue(ok(prices({ date: "2027-03-01", price: 300 })));
    renderFr(<MarketsView />);
    expect(screen.getByText("Prix attendu : Oignon, Thiaroye (Dakar)")).toBeInTheDocument();
    expect(screen.getByText(/\+10 % par rapport au dernier prix observé/)).toBeInTheDocument();
    expect(screen.getByText(/Prévision indicative/)).toBeInTheDocument();
  });

  it("n'invente pas d'écart sans prix observé", () => {
    mocks.prices.mockReturnValue(ok(prices(null)));
    renderFr(<MarketsView />);
    expect(screen.getByText("Aucun prix observé récemment")).toBeInTheDocument();
    expect(screen.queryByText(/par rapport au dernier prix observé/)).not.toBeInTheDocument();
  });

  it("change de culture avec le sélecteur", async () => {
    mocks.prices.mockReturnValue(ok(prices(null)));
    renderFr(<MarketsView />);
    await userEvent.click(screen.getByRole("radio", { name: "Tomate" }));
    expect(mocks.prices).toHaveBeenLastCalledWith("tomate", "thiaroye");
  });
});

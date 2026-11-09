// @vitest-environment jsdom
import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FertilizationView } from "@/features/fertilization/FertilizationView";
import { IrrigationView } from "@/features/irrigation/IrrigationView";
import { PestRiskView } from "@/features/pest-risk/PestRiskView";

import { makeProvenance, renderFr } from "./render";

type Query = { isPending: boolean; error: Error | null; data: unknown; refetch: () => Promise<unknown> };

const mocks = vi.hoisted(() => ({
  need: vi.fn(),
  weather: vi.fn(),
  fert: vi.fn(),
  pest: vi.fn(),
  allFields: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/fr/irrigation",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/services/ai/irrigation-need", () => ({ useIrrigationNeed: mocks.need }));
vi.mock("@/services/ai/weather", () => ({ useWeather: mocks.weather }));
vi.mock("@/services/ai/fertilization", () => ({ useFertilization: mocks.fert }));
vi.mock("@/services/ai/pest-risk", () => ({ usePestRisk: mocks.pest }));
vi.mock("@/hooks/places", () => ({ useAllFields: mocks.allFields }));

const ok = (data: unknown): Query => ({ isPending: false, error: null, data, refetch: vi.fn() });

const FARM = { id: "farm-1", name: "Ferme des Niayes" };
const FIELD = { id: "field-1", name: "Parcelle Nord", farm_id: "farm-1" };

beforeEach(() => {
  vi.clearAllMocks();
  mocks.allFields.mockReturnValue({
    fields: [FIELD],
    farms: [FARM],
    isPending: false,
    error: null,
    refetch: vi.fn(),
  });
  mocks.weather.mockReturnValue(ok({ days: [], provenance: makeProvenance() }));
});

describe("Irrigation (service 3)", () => {
  const need = (over: Record<string, unknown> = {}) => ({
    field_id: "field-1",
    window_hours: 24,
    need_mm: 5.5,
    volume_m3: 22,
    defer: false,
    defer_reason: null,
    rain_expected_mm: null,
    provenance: makeProvenance(),
    ...over,
  });

  it("présente le besoin dans une carte d'IA avec son état de fraîcheur", () => {
    mocks.need.mockReturnValue(ok(need()));
    renderFr(<IrrigationView initialFieldId="field-1" />);
    const card = screen.getByRole("region", { name: "Besoin en eau à 24 h" });
    expect(within(card).getByText("5,5 mm sur les 24 prochaines heures")).toBeInTheDocument();
    expect(within(card).getAllByText("À jour").length).toBeGreaterThan(0);
    expect(screen.queryByText("Arrosage reporté")).not.toBeInTheDocument();
  });

  it("annonce le report et ne présente jamais un résultat périmé comme à jour", () => {
    mocks.need.mockReturnValue(
      ok(
        need({
          defer: true,
          defer_reason: "Pluie attendue demain",
          rain_expected_mm: 12,
          provenance: makeProvenance({ stale: true }),
        }),
      ),
    );
    renderFr(<IrrigationView initialFieldId="field-1" />);
    const card = screen.getByRole("region", { name: "Besoin en eau à 24 h" });
    expect(within(card).getByText("Arrosage reporté")).toBeInTheDocument();
    expect(within(card).getByText("Pluie attendue demain")).toBeInTheDocument();
    expect(within(card).getAllByText("Périmé").length).toBeGreaterThan(0);
    expect(within(card).queryAllByText("À jour")).toHaveLength(0);
  });

  it("n'invente pas de volume quand il n'est pas calculé", () => {
    mocks.need.mockReturnValue(ok(need({ volume_m3: null })));
    renderFr(<IrrigationView initialFieldId="field-1" />);
    expect(screen.getByText("Non calculé")).toBeInTheDocument();
  });
});

describe("Fertilisation (service 6)", () => {
  const result = (over: Record<string, unknown> = {}) => ({
    field_id: "field-1",
    crop: "oignon",
    stage: "croissance",
    n_kg_ha: 80,
    p_kg_ha: null,
    k_kg_ha: 40,
    npk_class: "moyen",
    indicative: true,
    caveat: "À confirmer avec votre technicien.",
    provenance: makeProvenance({ fallback_step: 1 }),
    ...over,
  });

  it("affiche les trois doses, signale les valeurs indicatives et la valeur de secours", () => {
    mocks.fert.mockReturnValue(ok(result()));
    renderFr(<FertilizationView initialFieldId="field-1" />);
    const card = screen.getByRole("region", { name: "Doses conseillées" });
    expect(within(card).getByText("80 kg/ha")).toBeInTheDocument();
    expect(within(card).getByText("40 kg/ha")).toBeInTheDocument();
    expect(within(card).getByText("Pas de dose calculée")).toBeInTheDocument();
    expect(within(card).getByText("Valeurs indicatives")).toBeInTheDocument();
    expect(within(card).getAllByText("Valeur de secours").length).toBeGreaterThan(0);
  });

  it("ne montre pas le bandeau indicatif quand le contrat ne le demande pas", () => {
    mocks.fert.mockReturnValue(ok(result({ indicative: false, provenance: makeProvenance() })));
    renderFr(<FertilizationView initialFieldId="field-1" />);
    expect(screen.queryByText("Valeurs indicatives")).not.toBeInTheDocument();
  });
});

describe("Risques phytosanitaires (service 9)", () => {
  const risk = (calibrated: boolean) => ({
    field_id: "field-1",
    pests: [
      {
        pest_code: "thrips_tabaci",
        level: "high",
        p_outbreak_7d: 0.42,
        p_outbreak_14d: null,
        factors: ["Chaleur sèche"],
      },
    ],
    provenance: makeProvenance({
      confidence: { kind: "probability", value: 0.5, p10: null, p90: null, calibrated },
    }),
  });

  it("n'affiche une probabilité en pourcentage que si elle est calibrée", () => {
    mocks.pest.mockReturnValue(ok(risk(true)));
    renderFr(<PestRiskView initialFieldId="field-1" />);
    expect(screen.getByText(/42\s?%/)).toBeInTheDocument();
    expect(screen.getByText("Chaleur sèche")).toBeInTheDocument();
  });

  it("remplace le pourcentage par « probabilité non calibrée » sinon", () => {
    mocks.pest.mockReturnValue(ok(risk(false)));
    renderFr(<PestRiskView initialFieldId="field-1" />);
    expect(screen.queryByText(/42\s?%/)).not.toBeInTheDocument();
    expect(screen.getAllByText("probabilité non calibrée").length).toBeGreaterThan(0);
  });
});

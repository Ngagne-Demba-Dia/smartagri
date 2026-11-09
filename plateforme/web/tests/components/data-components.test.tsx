// @vitest-environment jsdom
import { fireEvent, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { AiCard } from "@/components/AiCard";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { KpiCard } from "@/components/KpiCard";
import { Meter } from "@/components/Meter";
import { Segmented } from "@/components/Segmented";
import { Sparkline, sparklinePoints } from "@/components/Sparkline";
import { Steps } from "@/components/Steps";

import { makeProvenance, renderFr } from "./render";

describe("KpiCard", () => {
  it("expose le libellé et la valeur comme terme et définition", () => {
    renderFr(
      <dl>
        <KpiCard label="Humidité" value="42" unit="%" hint="Il y a 5 min" />
      </dl>,
    );
    expect(screen.getByText("Humidité").closest("dt")).toBeInTheDocument();
    expect(screen.getByText("42").closest("dd")).toHaveTextContent("42%");
    expect(screen.getByText("Il y a 5 min")).toBeInTheDocument();
  });
});

describe("Meter", () => {
  it("annonce une valeur texte et borne la longueur dans la jauge", () => {
    renderFr(<Meter value={250} min={0} max={100} label="Remplissage" valueText="100 %" />);
    const meter = screen.getByRole("meter", { name: "Remplissage" });
    expect(meter).toHaveAttribute("aria-valuetext", "100 %");
    expect(meter.querySelectorAll("rect")[1]).toHaveAttribute("width", "100");
  });
});

describe("Sparkline", () => {
  it("trace une série plate au milieu et ne rend rien sous deux points", () => {
    expect(sparklinePoints([5, 5])).toBe("2.0,16.0 118.0,16.0");
    expect(sparklinePoints([])).toBe("");
    const { container } = renderFr(<Sparkline values={[1]} label="Tendance" />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("place le minimum en bas et le maximum en haut", () => {
    expect(sparklinePoints([0, 10])).toBe("2.0,30.0 118.0,2.0");
  });
});

describe("ConfidenceBadge", () => {
  it("ne montre jamais un pourcentage pour une confiance non calibrée", () => {
    renderFr(
      <ConfidenceBadge
        confidence={{ kind: "probability", value: 0.93, p10: null, p90: null, calibrated: false }}
      />,
    );
    expect(screen.getByText(/Non calibrée/)).toBeInTheDocument();
    expect(screen.queryByText(/93/)).toBeNull();
  });

  it("affiche l'intervalle calibré avec son unité", () => {
    renderFr(<ConfidenceBadge confidence={makeProvenance().confidence} unit=" mm" />);
    expect(screen.getByText(/Entre 4,1 mm et 7,9 mm/)).toBeInTheDocument();
  });
});

describe("AiCard", () => {
  it("affiche l'état, la confiance et un détail de provenance replié", () => {
    renderFr(
      <AiCard title="Besoin en eau" provenance={makeProvenance()}>
        <p>6 mm</p>
      </AiCard>,
    );
    expect(screen.getByRole("heading", { name: "Besoin en eau" })).toBeInTheDocument();
    expect(screen.getAllByText("À jour").length).toBeGreaterThan(0);
    expect(screen.getByText("6 mm")).toBeInTheDocument();
    expect(screen.getByText("Provenance").closest("details")).not.toHaveAttribute("open");
  });

  it("signale une valeur de secours et une valeur périmée, jamais « à jour »", () => {
    const { unmount } = renderFr(
      <AiCard title="A" provenance={makeProvenance({ fallback_step: 2, source: "rules" })}>
        x
      </AiCard>,
    );
    expect(screen.getAllByText("Valeur de secours").length).toBeGreaterThan(0);
    expect(screen.queryAllByText("À jour")).toHaveLength(0);
    unmount();
    renderFr(
      <AiCard title="B" provenance={makeProvenance({ stale: true })}>
        x
      </AiCard>,
    );
    expect(screen.getAllByText("Périmé").length).toBeGreaterThan(0);
    expect(screen.queryAllByText("À jour")).toHaveLength(0);
  });

  it("dit « provenance non communiquée » quand le bloc manque", () => {
    renderFr(
      <AiCard title="C" provenance={null}>
        x
      </AiCard>,
    );
    expect(screen.getByText(/Provenance non communiquée/)).toBeInTheDocument();
  });
});

describe("Segmented", () => {
  function Harness({ onPick }: { onPick: (v: string) => void }) {
    const [value, setValue] = useState("24");
    return (
      <Segmented
        legend="Horizon"
        value={value}
        onChange={(next) => {
          setValue(next);
          onPick(next);
        }}
        options={[
          { value: "24", label: "24 h" },
          { value: "48", label: "48 h" },
        ]}
      />
    );
  }

  it("expose un groupe de boutons radio et notifie le choix", () => {
    const onPick = vi.fn();
    renderFr(<Harness onPick={onPick} />);
    expect(screen.getByRole("group", { name: "Horizon" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "24 h" })).toBeChecked();
    fireEvent.click(screen.getByRole("radio", { name: "48 h" }));
    expect(onPick).toHaveBeenCalledWith("48");
    expect(screen.getByRole("radio", { name: "48 h" })).toBeChecked();
  });
});

describe("Steps", () => {
  it("marque l'étape courante et écrit l'état en toutes lettres", () => {
    renderFr(
      <Steps
        label="Cycle"
        stateLabels={{ done: "Fait", current: "En cours", todo: "À venir" }}
        items={[
          { key: "sow", label: "Semis", state: "done", detail: "3 janv." },
          { key: "grow", label: "Croissance", state: "current" },
          { key: "harvest", label: "Récolte", state: "todo" },
        ]}
      />,
    );
    expect(screen.getByRole("list", { name: "Cycle" })).toBeInTheDocument();
    expect(screen.getByText("Croissance").closest("li")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Fait · 3 janv.")).toBeInTheDocument();
    expect(screen.getByText("À venir")).toBeInTheDocument();
  });
});

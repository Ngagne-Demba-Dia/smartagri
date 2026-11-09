import { describe, expect, it } from "vitest";

import { groupPests, highestLevel, probabilityView, type PestEntry } from "@/lib/pests";

const entry = (code: string, level: PestEntry["level"]): PestEntry => ({
  pest_code: code,
  level,
  p_outbreak_7d: 0.4,
  p_outbreak_14d: 0.5,
  factors: [],
});

describe("highestLevel", () => {
  it("renvoie le niveau le plus élevé, null sans organisme", () => {
    expect(highestLevel([entry("a", "low"), entry("b", "high"), entry("c", "medium")])).toBe("high");
    expect(highestLevel([entry("a", "low")])).toBe("low");
    expect(highestLevel([])).toBeNull();
  });
});

describe("groupPests", () => {
  it("répartit selon le dictionnaire, code inconnu en non classé", () => {
    const kinds = { thrips: "pest", mildiou: "disease" } as const;
    const groups = groupPests(
      [entry("thrips", "low"), entry("mildiou", "high"), entry("inconnu", "medium")],
      (code) => (kinds as Record<string, "pest" | "disease">)[code] ?? null,
    );
    expect(groups.pest.map((p) => p.pest_code)).toEqual(["thrips"]);
    expect(groups.disease.map((p) => p.pest_code)).toEqual(["mildiou"]);
    expect(groups.unclassified.map((p) => p.pest_code)).toEqual(["inconnu"]);
  });
});

describe("probabilityView", () => {
  it("n'affiche un pourcentage que si la probabilité est calibrée", () => {
    expect(probabilityView(0.42, true)).toEqual({ type: "percent", value: 42 });
    expect(probabilityView(0.42, false)).toEqual({ type: "uncalibrated" });
  });

  it("null reste « sans valeur »", () => {
    expect(probabilityView(null, true)).toEqual({ type: "none" });
  });
});

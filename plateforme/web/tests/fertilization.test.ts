import { describe, expect, it } from "vitest";

import type { Fertilization } from "@/lib/contracts/field";
import { doseOf, hasAnyDose, isDegraded, readingKind } from "@/lib/fertilization";

const result = (over: Partial<Fertilization> = {}, stale = false): Fertilization => ({
  field_id: "f",
  crop: "mil",
  stage: "levée",
  n_kg_ha: 40,
  p_kg_ha: 20,
  k_kg_ha: 10,
  npk_class: "bas",
  indicative: true,
  caveat: "Valeurs indicatives.",
  provenance: {
    model_name: "fert_reco",
    model_version: "1",
    source: "agriml",
    fallback_step: 0,
    computed_at: "2026-11-09T08:00:00Z",
    data_as_of: null,
    stale,
    confidence: { kind: "none", value: null, p10: null, p90: null, calibrated: false },
  },
  ...over,
});

describe("doses", () => {
  it("lit chaque dose du contrat", () => {
    const r = result();
    expect([doseOf(r, "n"), doseOf(r, "p"), doseOf(r, "k")]).toEqual([40, 20, 10]);
  });

  it("hasAnyDose est faux quand toutes les doses sont nulles", () => {
    expect(hasAnyDose(result())).toBe(true);
    expect(hasAnyDose(result({ n_kg_ha: null, p_kg_ha: null, k_kg_ha: null }))).toBe(false);
    expect(hasAnyDose(result({ n_kg_ha: null, p_kg_ha: null, k_kg_ha: 0 }))).toBe(true);
  });
});

describe("readingKind et isDegraded", () => {
  it("distingue avec et sans dose", () => {
    expect(readingKind(result())).toBe("withDose");
    expect(readingKind(result({ n_kg_ha: null, p_kg_ha: null, k_kg_ha: null }))).toBe("noDose");
  });

  it("signale un résultat périmé", () => {
    expect(isDegraded(result())).toBe(false);
    expect(isDegraded(result({}, true))).toBe(true);
  });
});

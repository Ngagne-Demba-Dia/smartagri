import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import type { KitParameters } from "@/lib/contracts/device";
import { blockStatus, isNotPublished, validityDays } from "@/lib/kit";

const NOW = new Date("2026-11-09T12:00:00Z");

const prov = (computedAt: string, over: { stale?: boolean; fallback_step?: number } = {}) => ({
  model_name: "irr_water_balance",
  model_version: "1",
  source: "agriml" as const,
  fallback_step: over.fallback_step ?? 0,
  computed_at: computedAt,
  data_as_of: null,
  stale: over.stale ?? false,
  confidence: {
    kind: "none" as const,
    value: null,
    p10: null,
    p90: null,
    calibrated: false,
  },
});

const params = (seuils: ReturnType<typeof prov>): KitParameters =>
  ({
    provenance: {
      seuils,
      npk: prov("2026-11-09T08:00:00Z"),
      etalonnage: prov("2026-11-09T08:00:00Z"),
      agro: prov("2026-11-09T08:00:00Z"),
    },
  }) as unknown as KitParameters;

describe("blockStatus", () => {
  it("fresh quand le bloc est récent", () => {
    expect(blockStatus(params(prov("2026-11-08T12:00:00Z")), "seuils", NOW)).toBe("fresh");
  });

  it("expired au-delà de la durée de validité, même sans drapeau stale", () => {
    expect(blockStatus(params(prov("2026-10-30T12:00:00Z")), "seuils", NOW)).toBe("expired");
  });

  it("stale et fallback viennent de la provenance", () => {
    expect(blockStatus(params(prov("2026-11-09T08:00:00Z", { stale: true })), "seuils", NOW)).toBe("stale");
    expect(blockStatus(params(prov("2026-11-09T08:00:00Z", { fallback_step: 1 })), "seuils", NOW)).toBe(
      "fallback",
    );
  });
});

describe("validityDays et isNotPublished", () => {
  it("expose les durées du doc 16", () => {
    expect(validityDays("seuils")).toBe(7);
    expect(validityDays("etalonnage")).toBe(180);
  });

  it("un 404 est un état vide, pas une erreur", () => {
    expect(isNotPublished(new ApiError("NOT_FOUND", "x", 404))).toBe(true);
    expect(isNotPublished(new ApiError("UPSTREAM_UNAVAILABLE", "x", 503))).toBe(false);
    expect(isNotPublished(new Error("x"))).toBe(false);
  });
});

import { describe, expect, it } from "vitest";

import type { Diagnosis } from "@/lib/contracts/assistant";
import {
  checkImageFile,
  diagnosisVerdict,
  encodeWithinLimit,
  fitWithin,
  JPEG_QUALITIES,
  MAX_IMAGE_SIDE,
  MAX_SOURCE_BYTES,
  topProbability,
  VERDICT_TONE,
} from "@/lib/diagnosis";

const diagnosis = (patch: Partial<Diagnosis>): Diagnosis =>
  ({
    id: null,
    label: "sick",
    disease_code: "downy_mildew",
    top3: [{ code: "downy_mildew", probability: 0.86 }],
    abstained: false,
    captured_at: "2026-11-09T08:00:00Z",
    provenance: {},
    ...patch,
  }) as unknown as Diagnosis;

const blobOf = (size: number) => new Blob([new Uint8Array(size)]);

describe("checkImageFile", () => {
  it("accepte JPEG, PNG et WebP dans la limite de taille", () => {
    for (const type of ["image/jpeg", "image/png", "image/webp"]) {
      expect(checkImageFile({ type, size: 1000 })).toBe("ok");
    }
    expect(checkImageFile({ type: "image/jpeg", size: MAX_SOURCE_BYTES })).toBe("ok");
  });

  it("refuse un autre format, un fichier vide et un fichier trop lourd", () => {
    expect(checkImageFile({ type: "image/heic", size: 1000 })).toBe("type");
    expect(checkImageFile({ type: "application/pdf", size: 1000 })).toBe("type");
    expect(checkImageFile({ type: "image/png", size: 0 })).toBe("empty");
    expect(checkImageFile({ type: "image/png", size: MAX_SOURCE_BYTES + 1 })).toBe("size");
  });
});

describe("fitWithin", () => {
  it("réduit en gardant les proportions et n'agrandit jamais", () => {
    expect(fitWithin(4000, 3000, 1000)).toEqual({ width: 1000, height: 750 });
    expect(fitWithin(3000, 4000, 1000)).toEqual({ width: 750, height: 1000 });
    expect(fitWithin(800, 600, 1000)).toEqual({ width: 800, height: 600 });
  });

  it("garde au moins un pixel sur le petit côté", () => {
    expect(fitWithin(10_000, 1, 100)).toEqual({ width: 100, height: 1 });
  });
});

describe("encodeWithinLimit", () => {
  it("baisse la qualité avant de réduire la taille", async () => {
    const calls: Array<[number, number]> = [];
    const blob = await encodeWithinLimit(async (side, quality) => {
      calls.push([side, quality]);
      return blobOf(quality > 0.6 ? 500 : 100);
    }, 200);
    expect(blob?.size).toBe(100);
    expect(calls).toEqual([
      [MAX_IMAGE_SIDE, JPEG_QUALITIES[0]],
      [MAX_IMAGE_SIDE, JPEG_QUALITIES[1]],
      [MAX_IMAGE_SIDE, JPEG_QUALITIES[2]],
    ]);
  });

  it("réduit la taille quand la qualité ne suffit pas", async () => {
    const sides: number[] = [];
    const blob = await encodeWithinLimit(async (side) => {
      sides.push(side);
      return blobOf(side > 800 ? 500 : 100);
    }, 200);
    expect(blob?.size).toBe(100);
    expect(Math.max(...sides)).toBe(MAX_IMAGE_SIDE);
    expect(sides.at(-1)).toBeLessThanOrEqual(768);
  });

  it("renvoie null, en un nombre fini d'essais, si rien ne tient", async () => {
    let attempts = 0;
    const blob = await encodeWithinLimit(async () => {
      attempts += 1;
      return blobOf(1000);
    }, 200);
    expect(blob).toBeNull();
    expect(attempts).toBeGreaterThan(0);
    expect(attempts).toBeLessThanOrEqual(30);
  });
});

describe("diagnosisVerdict", () => {
  it("reprend l'étiquette quand la première hypothèse atteint le seuil de 0,7", () => {
    expect(diagnosisVerdict(diagnosis({}))).toBe("sick");
    expect(
      diagnosisVerdict(diagnosis({ label: "healthy", top3: [{ code: "healthy", probability: 0.7 }] })),
    ).toBe("healthy");
    expect(diagnosisVerdict(diagnosis({ label: "suspect" }))).toBe("suspect");
  });

  it("répond « incertain » si le service s'abstient, même avec une étiquette affirmative", () => {
    expect(diagnosisVerdict(diagnosis({ abstained: true }))).toBe("uncertain");
  });

  it("répond « incertain » sous 0,7 même si le service ne s'est pas abstenu", () => {
    expect(diagnosisVerdict(diagnosis({ top3: [{ code: "downy_mildew", probability: 0.69 }] }))).toBe(
      "uncertain",
    );
  });

  it("répond « incertain » sans aucune hypothèse", () => {
    expect(diagnosisVerdict(diagnosis({ top3: [] }))).toBe("uncertain");
    expect(topProbability(diagnosis({ top3: [] }))).toBeNull();
  });

  it("associe un ton à chaque verdict, l'incertitude restant neutre", () => {
    expect(VERDICT_TONE).toEqual({ healthy: "ok", sick: "bad", suspect: "warn", uncertain: "info" });
  });
});

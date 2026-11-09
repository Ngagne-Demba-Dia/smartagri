import { describe, expect, it } from "vitest";

import type { DeviceHealth } from "@/lib/contracts/device";
import { pumpRiskView, sensorTone, worstState } from "@/lib/device-health";

const sensor = (state: DeviceHealth["sensors"][number]["state"]) => ({
  sensor: "soil" as const,
  state,
  since: null,
});

describe("worstState", () => {
  it("renvoie l'état le plus grave : défaut, puis dégradé, puis non installé", () => {
    expect(worstState([sensor("ok"), sensor("absent"), sensor("degraded")])).toBe("degraded");
    expect(worstState([sensor("degraded"), sensor("fault"), sensor("ok")])).toBe("fault");
    expect(worstState([sensor("ok"), sensor("absent")])).toBe("absent");
    expect(worstState([sensor("ok")])).toBe("ok");
  });

  it("renvoie null sans capteur", () => {
    expect(worstState([])).toBeNull();
  });
});

describe("sensorTone", () => {
  it("associe un ton à chaque état", () => {
    expect(sensorTone("ok")).toBe("ok");
    expect(sensorTone("absent")).toBe("info");
    expect(sensorTone("degraded")).toBe("warn");
    expect(sensorTone("fault")).toBe("bad");
  });
});

describe("pumpRiskView", () => {
  it("n'affiche un pourcentage que si le risque est calibré", () => {
    expect(pumpRiskView(0.62, true)).toEqual({ type: "percent", value: 62 });
    expect(pumpRiskView(0.62, false)).toEqual({ type: "uncalibrated" });
    expect(pumpRiskView(null, true)).toEqual({ type: "none" });
  });
});

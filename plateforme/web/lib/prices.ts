/** Prix de marché (service 15) : FCFA/kg à 1–4 semaines, écart à la dernière observation. */
import type { PriceForecast } from "./contracts/org";

export type PriceHorizon = PriceForecast["horizons"][number];

/** Cultures suivies (clés en minuscules : l'API répond 404 sinon). */
export const PRICE_CROPS = ["oignon", "tomate", "chou", "carotte", "pomme de terre"] as const;
export type PriceCrop = (typeof PRICE_CROPS)[number];

/** Marchés proposés ; l'API accepte tout identifiant non vide (liste à confirmer avec le service de prix). */
export const PRICE_MARKETS = ["thiaroye", "kaolack", "saint-louis"] as const;
export type PriceMarket = (typeof PRICE_MARKETS)[number];

export function sortedPriceHorizons(horizons: readonly PriceHorizon[]): PriceHorizon[] {
  return [...horizons].sort((a, b) => a.weeks - b.weeks);
}

/** Variation de la médiane par rapport au dernier prix observé, en %, arrondie à l'unité ; null sans observation. */
export function changePct(observed: number | null, p50: number): number | null {
  if (observed === null || observed <= 0) return null;
  const rounded = Math.round(((p50 - observed) / observed) * 100);
  return rounded === 0 ? 0 : rounded;
}

/** Clé de traduction d'une culture : espaces remplacés par « _ » (« pomme de terre » → « pomme_de_terre »). */
export function cropKey(crop: string): string {
  return crop.replace(/\s+/g, "_");
}

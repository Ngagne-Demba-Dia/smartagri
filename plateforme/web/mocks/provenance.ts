/**
 * Bloc de provenance simulé (doc 16 §9.2) : une table explicite, par service, du modèle nominal et de
 * sa valeur de secours (chaîne bundle → lot OctOpus → règles). Les identifiants viennent du catalogue
 * agriml (doc 14) ; les versions sont fictives. Les scénarios décident de la fraîcheur et du repli.
 */
import type { Confidence, Provenance, ProvenanceSource } from "@/lib/contracts/provenance";
import { serviceById, type ServiceId } from "@/lib/contracts/registry";

import { HOUR_MS, iso } from "./base";
import type { MockScenario } from "./scenario";

export interface ModelRef {
  name: string;
  version: string;
  source: ProvenanceSource;
}

interface Plan {
  nominal: ModelRef;
  fallback: ModelRef & { step: 1 | 2 };
}

const m = (name: string, version: string, source: ProvenanceSource): ModelRef => ({ name, version, source });
const fb = (name: string, version: string, step: 1 | 2, source: ProvenanceSource) => ({ name, version, step, source });

const PLAN: Readonly<Record<ServiceId, Plan>> = {
  weather: { nominal: m("wx_blend", "2", "agriml"), fallback: fb("irr_et0", "1", 2, "rules") },
  soil_forecast: { nominal: m("soil_nowcast", "2", "agriml"), fallback: fb("soil_nowcast", "2", 1, "octopus") },
  irrigation_need: { nominal: m("irr_need_24h", "3", "agriml"), fallback: fb("irr_water_balance", "2", 2, "rules") },
  irrigation_plan: { nominal: m("irr_scheduler", "1", "agriml"), fallback: fb("irr_scheduler", "1", 1, "octopus") },
  recommendations: { nominal: m("reco_engine", "2", "agriml"), fallback: fb("risk_rules", "1", 2, "rules") },
  fertilization: { nominal: m("fert_reco", "1", "agriml"), fallback: fb("fert_reco", "1", 2, "rules") },
  kit_parameters: { nominal: m("irr_water_balance", "2", "agriml"), fallback: fb("irr_water_balance", "2", 2, "rules") },
  disease_diagnosis: { nominal: m("vis_disease", "4", "agriml"), fallback: fb("vis_disease", "3", 1, "octopus") },
  pest_risk: { nominal: m("pest_phenology", "1", "agriml"), fallback: fb("risk_rules", "1", 2, "rules") },
  trap_counts: { nominal: m("vis_pest_count", "1", "agriml"), fallback: fb("vis_pest_count", "1", 1, "octopus") },
  vegetation: { nominal: m("ndvi_gapfill", "2", "octopus"), fallback: fb("ndvi_gapfill", "2", 2, "rules") },
  yield_forecast: { nominal: m("yield_forecast", "2", "octopus"), fallback: fb("yield_crop_model", "1", 2, "rules") },
  device_health: { nominal: m("pump_health", "1", "agriml"), fallback: fb("anomaly_rules", "3", 2, "rules") },
  water_savings: { nominal: m("water_savings", "1", "octopus"), fallback: fb("water_savings", "1", 2, "rules") },
  price_forecast: { nominal: m("price_forecast", "1", "octopus"), fallback: fb("price_forecast", "1", 2, "rules") },
  assistant_chat: { nominal: m("asst_llm", "3", "agriml"), fallback: fb("asst_retrieval", "2", 2, "rules") },
  assistant_transcribe: { nominal: m("asst_asr", "1", "agriml"), fallback: fb("asst_asr", "1", 1, "octopus") },
  map_layers: { nominal: m("field_boundary", "1", "octopus"), fallback: fb("field_boundary", "1", 2, "rules") },
};

/** Paramètres du kit : un modèle par bloc (doc 16 §7). */
export const KIT_BLOCK_MODELS = {
  seuils: m("irr_water_balance", "2", "agriml"),
  npk: m("fert_reco", "1", "agriml"),
  etalonnage: m("sm_calibration", "1", "agriml"),
  agro: m("irr_water_balance", "2", "agriml"),
} as const;

/** Couches de la carte : chacune a sa propre provenance (MapLayersSchema.layers). */
export const MAP_LAYER_MODELS = {
  crop_type: m("crop_type_map", "1", "octopus"),
  salinity: m("salinity_risk", "1", "octopus"),
  field_boundary: m("field_boundary", "1", "octopus"),
} as const;

/* ---------- Confiance ---------- */

export const NO_CONFIDENCE: Confidence = { kind: "none", value: null, p10: null, p90: null, calibrated: false };

export const probability = (value: number, calibrated: boolean): Confidence => ({
  kind: "probability", value: clamp01(value), p10: null, p90: null, calibrated,
});

export const classProbability = (value: number | null, calibrated: boolean): Confidence => ({
  kind: "class_probability", value: value === null ? null : clamp01(value), p10: null, p90: null, calibrated,
});

export function interval(p10: number, p90: number, calibrated: boolean): Confidence {
  const [low, high] = p10 <= p90 ? [p10, p90] : [p90, p10];
  return { kind: "interval", value: null, p10: low, p90: high, calibrated };
}

function clamp01(value: number): number {
  return Math.round(Math.min(1, Math.max(0, value)) * 1000) / 1000;
}

/* ---------- Bloc de provenance ---------- */

const NOMINAL_AGE_MS = 5 * 60_000;
const NOMINAL_DATA_AGE_MS = 15 * 60_000;
const MIN_STALE_AGE_MS = 3 * HOUR_MS;

export interface ProvenanceOptions {
  /** Remplace le modèle nominal (paramètres du kit, couches de carte). */
  model?: ModelRef;
  /** Confiance nominale, tirée de la charge utile. */
  confidence?: Confidence;
  /** Garde la confiance en repli ou en abstention (diagnostic : la probabilité explique l'abstention). */
  keepConfidence?: boolean;
  /** Dernière donnée d'entrée (mesure du kit, image satellite) ; défaut : il y a 15 min. */
  dataAsOf?: Date | null;
}

export function provenance(
  service: ServiceId,
  scenario: MockScenario,
  now: Date,
  options: ProvenanceOptions = {},
): Provenance {
  const plan = PLAN[service];
  const useFallback = scenario === "fallback";
  const model = useFallback ? plan.fallback : (options.model ?? plan.nominal);
  const degraded = scenario === "fallback" || scenario === "abstention";
  const confidence = degraded && !options.keepConfidence ? NO_CONFIDENCE : (options.confidence ?? NO_CONFIDENCE);

  if (scenario === "stale") {
    const age = Math.max(2 * serviceById(service).staleMs, MIN_STALE_AGE_MS);
    const computed = new Date(now.getTime() - age);
    return {
      model_name: model.name,
      model_version: model.version,
      source: model.source,
      fallback_step: 0,
      computed_at: iso(computed),
      data_as_of: iso(new Date(computed.getTime() - HOUR_MS)),
      stale: true,
      confidence,
    };
  }

  const dataAsOf = options.dataAsOf === undefined ? new Date(now.getTime() - NOMINAL_DATA_AGE_MS) : options.dataAsOf;
  return {
    model_name: model.name,
    model_version: model.version,
    source: model.source,
    fallback_step: useFallback ? plan.fallback.step : 0,
    computed_at: iso(new Date(now.getTime() - NOMINAL_AGE_MS)),
    data_as_of: dataAsOf === null ? null : iso(dataAsOf),
    stale: false,
    confidence,
  };
}

/** Modèle nominal d'un service (version affichée par l'interface et les tests). */
export const nominalModel = (service: ServiceId): ModelRef => PLAN[service].nominal;

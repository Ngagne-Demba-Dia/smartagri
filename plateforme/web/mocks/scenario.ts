/**
 * Scénarios de doc 16 §9.5 : chaque service simulé sait répondre en nominal, périmé, repli, abstention,
 * erreur 503 et vide. Un scénario global, initialisé par AGRI_MOCK_SCENARIO, et des surcharges par service,
 * pilotés en développement par POST /api/dev/mock. L'état vit sur globalThis (rechargements à chaud de Next).
 */
import { SERVICE_IDS, type ServiceId } from "@/lib/contracts/registry";
import { MOCK_SCENARIOS, type MockScenario } from "@/lib/mock-config";

export { MOCK_SCENARIOS, type MockScenario };

export interface ScenarioSnapshot {
  global: MockScenario;
  overrides: Partial<Record<ServiceId, MockScenario>>;
}

const KEY = Symbol.for("smartagri92.mock.scenario");
type Holder = Record<symbol, ScenarioSnapshot | undefined>;

export function isScenario(value: unknown): value is MockScenario {
  return typeof value === "string" && (MOCK_SCENARIOS as readonly string[]).includes(value);
}

export function isServiceId(value: unknown): value is ServiceId {
  return typeof value === "string" && (SERVICE_IDS as readonly string[]).includes(value);
}

function initial(): ScenarioSnapshot {
  const fromEnv = process.env.AGRI_MOCK_SCENARIO;
  return { global: isScenario(fromEnv) ? fromEnv : "nominal", overrides: {} };
}

function read(): ScenarioSnapshot {
  const holder = globalThis as unknown as Holder;
  const current = holder[KEY];
  if (current) return current;
  const fresh = initial();
  holder[KEY] = fresh;
  return fresh;
}

function write(next: ScenarioSnapshot): ScenarioSnapshot {
  (globalThis as unknown as Holder)[KEY] = next;
  return next;
}

export function snapshot(): ScenarioSnapshot {
  const current = read();
  return { global: current.global, overrides: { ...current.overrides } };
}

export function scenarioFor(service: ServiceId): MockScenario {
  const current = read();
  return current.overrides[service] ?? current.global;
}

/** Sans service : change le scénario global ; avec : surcharge ce service seul. */
export function setScenario(scenario: MockScenario, service?: ServiceId): ScenarioSnapshot {
  const current = read();
  if (!service) return write({ ...current, global: scenario });
  return write({ ...current, overrides: { ...current.overrides, [service]: scenario } });
}

/** Retire la surcharge du service : il suit de nouveau le scénario global. */
export function clearScenario(service: ServiceId): ScenarioSnapshot {
  const current = read();
  const overrides = Object.fromEntries(Object.entries(current.overrides).filter(([id]) => id !== service));
  return write({ ...current, overrides });
}

export function resetScenarios(): ScenarioSnapshot {
  return write({ global: "nominal", overrides: {} });
}

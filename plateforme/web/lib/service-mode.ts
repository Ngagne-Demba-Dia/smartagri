/**
 * Mode hybride par service (Sprint D1) : même grammaire que le backend (`app/core/service_modes.py`).
 *
 *   AGRI_MOCK=1|0                      défaut de tous les services : simulation (1) ou API réelle (0)
 *   AGRI_SERVICES=irrigation_need=real,pest_risk=mock     exceptions au défaut, noms de doc 16 §9.3
 *
 * Une route est rattachée à un service par la table du registre (lib/contracts/registry.ts), source unique
 * des routes de doc 16. Une route hors registre (auth, fermes, alertes…) suit le défaut AGRI_MOCK. Module
 * neutre (ni « server-only » ni msw), testable directement.
 */
import { SERVICES, SERVICE_IDS, type ServiceId } from "@/lib/contracts/registry";
import { isMockMode } from "@/lib/mock-config";

export type ServiceMode = "real" | "mock";

/** Alias acceptés dans AGRI_SERVICES (doc 16 §9.3 nomme ce service « diagnosis_analyze »). */
const ALIASES: Readonly<Record<string, ServiceId>> = { diagnosis_analyze: "disease_diagnosis" };
const MODES: ReadonlySet<string> = new Set<ServiceMode>(["real", "mock"]);

/** AGRI_SERVICES invalide : une faute de frappe ne doit pas laisser un service en simulation sans bruit. */
export class ServiceModeError extends Error {}

function canonical(name: string): ServiceId {
  const key = name.trim();
  const id = ALIASES[key] ?? SERVICE_IDS.find((s) => s === key);
  if (!id) throw new ServiceModeError(`Service inconnu dans AGRI_SERVICES : « ${name} ».`);
  return id;
}

export function parseServiceOverrides(raw: string | undefined): ReadonlyMap<ServiceId, ServiceMode> {
  const overrides = new Map<ServiceId, ServiceMode>();
  for (const item of (raw ?? "").split(",").map((part) => part.trim()).filter(Boolean)) {
    const eq = item.indexOf("=");
    const mode = eq < 0 ? "" : item.slice(eq + 1).trim().toLowerCase();
    if (!MODES.has(mode)) throw new ServiceModeError(`Entrée AGRI_SERVICES invalide : « ${item} » (attendu nom=real|mock).`);
    overrides.set(canonical(item.slice(0, eq)), mode as ServiceMode);
  }
  return overrides;
}

export function defaultMode(): ServiceMode {
  return isMockMode() ? "mock" : "real";
}

export function serviceMode(service: ServiceId): ServiceMode {
  return parseServiceOverrides(process.env.AGRI_SERVICES).get(service) ?? defaultMode();
}

const escapeRegExp = (text: string): string => text.replace(/[\\^$.*+?()[\]{}|]/g, (char) => `\\${char}`);

/** `/v1/fields/{id}/weather?days=` → expression ancrée sur le chemin, query ignorée. */
function routePattern(template: string): RegExp {
  const path = template.split("?")[0] ?? template;
  const source = path
    .split("/")
    .map((segment) => (/^\{[a-z_]+\}$/.test(segment) ? "[^/]+" : escapeRegExp(segment)))
    .join("/");
  return new RegExp(`^${source}$`);
}

const EXTRA_SERVICE_ROUTES: ReadonlyArray<{ template: string; service: ServiceId }> = [
  { template: "/v1/devices/{id}/parameters/ack", service: "kit_parameters" },
];

const ROUTE_TABLE: ReadonlyArray<{ pattern: RegExp; service: ServiceId }> = [
  ...SERVICES.flatMap((def) => def.routes.map((route) => ({ pattern: routePattern(route.path), service: def.id }))),
  ...EXTRA_SERVICE_ROUTES.map((entry) => ({ pattern: routePattern(entry.template), service: entry.service })),
];

/** Service qui sert ce chemin d'API (`/v1/...`, sans query), ou null si la route n'appartient à aucun. */
export function serviceForPath(apiPath: string): ServiceId | null {
  return ROUTE_TABLE.find((entry) => entry.pattern.test(apiPath))?.service ?? null;
}

/** Mode de la route : celui de son service, sinon le défaut global. */
export function modeForPath(apiPath: string): ServiceMode {
  const service = serviceForPath(apiPath);
  return service ? serviceMode(service) : defaultMode();
}

/** Table complète des modes effectifs par service (utile pour l'inspection dev/mock). */
export function allServiceModes(): Record<ServiceId, ServiceMode> {
  const base = defaultMode();
  const overrides = parseServiceOverrides(process.env.AGRI_SERVICES);
  const result = {} as Record<ServiceId, ServiceMode>;
  for (const id of SERVICE_IDS) {
    result[id] = overrides.get(id) ?? base;
  }
  return result;
}

/**
 * Correspondance déterministe entre les slugs de démonstration (mocks) et les UUID v4 canoniques
 * créés par `python -m app.seed` côté backend. Permet le mode hybride (ex. liste des parcelles
 * servie par l'API réelle ou simulée et sous-ressources routées par service) sans jamais masquer
 * un vrai 404 par un repli simulé silencieux.
 */
export const DEMO_UUID_BY_SLUG: Readonly<Record<string, string>> = {
  "org-demo-niayes": "00000000-0000-4000-8000-000000000001",
  "farm-mboro": "00000000-0000-4000-8000-000000000101",
  "fld-mboro-1": "00000000-0000-4000-8000-000000000201",
  "dev-0001": "00000000-0000-4000-8000-000000000301",
  "cmp-contre-saison": "00000000-0000-4000-8000-000000000401",
  "cyc-fld-mboro-1": "00000000-0000-4000-8000-000000000501",
  "eq-mboro-pump": "00000000-0000-4000-8000-000000000601",
};

export const DEMO_SLUG_BY_UUID: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(DEMO_UUID_BY_SLUG).map(([slug, uuid]) => [uuid, slug]),
);

export function toRealId(id: string): string {
  return DEMO_UUID_BY_SLUG[id] ?? id;
}

export function toMockId(id: string): string {
  return DEMO_SLUG_BY_UUID[id.toLowerCase()] ?? id;
}

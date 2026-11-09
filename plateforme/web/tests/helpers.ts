/**
 * Outils communs des tests : requêtes vers les simulations MSW (doc 16 §9.5) sans serveur ni réseau,
 * lecture de l'enveloppe et collecte des blocs de provenance d'une réponse.
 */
import { createApiClient, type ApiClient } from "@/lib/api";
import type { DiagnosisInput } from "@/lib/contracts/assistant";
import { ProvenanceSchema, type Provenance } from "@/lib/contracts/provenance";
import type { ServiceId } from "@/lib/contracts/registry";
import { MOCK_BASE } from "@/lib/mock-config";
import { handleMock } from "@/mocks";

export type Role = "farmer" | "coop_manager" | "agronomist" | "admin";

export interface MockCall {
  method: "GET" | "POST" | "PUT";
  path: string;
  body?: unknown;
}

export interface EnvelopeBody {
  success: boolean;
  data: unknown;
  error: { code: string; message: string; details?: Record<string, unknown> } | null;
  meta: Record<string, unknown> | null;
}

export const bearer = (role: Role): Record<string, string> => ({
  authorization: `Bearer mock-access-${role}`,
});

/** Appel direct des gestionnaires ; `role: null` envoie la requête sans jeton. */
export function call(request: MockCall, role: Role | null = "admin"): Promise<Response> {
  const headers: Record<string, string> = role ? bearer(role) : {};
  if (request.body !== undefined) headers["content-type"] = "application/json";
  return handleMock(
    new Request(`${MOCK_BASE}${request.path}`, {
      method: request.method,
      headers,
      body: request.body === undefined ? undefined : JSON.stringify(request.body),
    }),
  );
}

export async function readEnvelope(response: Response): Promise<EnvelopeBody> {
  return (await response.json()) as EnvelopeBody;
}

export const get = (path: string): MockCall => ({ method: "GET", path });
export const post = (path: string, body?: unknown): MockCall => ({ method: "POST", path, body });
export const put = (path: string, body?: unknown): MockCall => ({ method: "PUT", path, body });

/** Client du front branché sur les simulations : même chemin que le navigateur, sans BFF. */
export function mockClient(role: Role = "admin"): ApiClient {
  return createApiClient({
    baseUrl: MOCK_BASE,
    fetchImpl: async (input, init) => {
      const headers = new Headers(init?.headers);
      headers.set("authorization", bearer(role).authorization ?? "");
      return handleMock(new Request(String(input), { ...init, headers }));
    },
  });
}

/** Tous les blocs de provenance (doc 16 §9.2) présents dans une charge utile, à toute profondeur. */
export function provenances(value: unknown): Provenance[] {
  const found: Provenance[] = [];
  const visit = (node: unknown): void => {
    if (Array.isArray(node)) {
      node.forEach(visit);
      return;
    }
    if (typeof node !== "object" || node === null) return;
    const parsed = ProvenanceSchema.safeParse(node);
    if (parsed.success) {
      found.push(parsed.data);
      return;
    }
    Object.values(node).forEach(visit);
  };
  visit(value);
  return found;
}

export const IMAGE_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAwS2OUAAAAABJRU5ErkJggg==";
export const AUDIO_BASE64 = "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";

export const diagnosisBody = (
  fieldId: string | null = "fld-mboro-1",
  deviceId: string | null = null,
): DiagnosisInput => ({
  image_base64: IMAGE_BASE64,
  content_type: "image/png",
  field_id: fieldId,
  device_id: deviceId,
  captured_at: "2026-11-09T08:00:00Z",
});

export const transcribeBody = (language: "wo" | "ff" | "fr" | null = "wo") => ({
  audio_base64: AUDIO_BASE64,
  content_type: "audio/wav",
  duration_s: 4,
  language_hint: language,
});

/** Un appel représentatif par service (route principale de doc 16 §9.3). */
export const SERVICE_CALLS: Readonly<Record<ServiceId, MockCall>> = {
  weather: get("/v1/fields/fld-mboro-1/weather?days=3"),
  soil_forecast: get("/v1/fields/fld-mboro-1/soil-forecast?horizons=24,48,72"),
  irrigation_need: get("/v1/fields/fld-mboro-1/irrigation-need"),
  irrigation_plan: get("/v1/farms/farm-mboro/irrigation-plan"),
  recommendations: get("/v1/fields/fld-mboro-1/recommendations"),
  fertilization: get("/v1/fields/fld-mboro-1/fertilization"),
  kit_parameters: get("/v1/devices/dev-0001/parameters"),
  disease_diagnosis: post("/v1/diagnoses/analyze", diagnosisBody()),
  pest_risk: get("/v1/fields/fld-mboro-1/pest-risk"),
  trap_counts: get("/v1/devices/dev-0001/trap-counts"),
  vegetation: get("/v1/fields/fld-mboro-1/vegetation"),
  yield_forecast: get("/v1/fields/fld-mboro-1/yield-forecast"),
  device_health: get("/v1/devices/dev-0001/health"),
  water_savings: get("/v1/reports/kpis"),
  price_forecast: get("/v1/markets/prices?crop=oignon&market=Thiaroye"),
  assistant_chat: post("/v1/assistant/chat", { message: "Quand arroser mes oignons ?" }),
  assistant_transcribe: post("/v1/assistant/transcribe", transcribeBody()),
  map_layers: get("/v1/farms/farm-mboro/map"),
};

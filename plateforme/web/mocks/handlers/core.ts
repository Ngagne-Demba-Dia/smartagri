/**
 * Gestionnaires MSW des routes du socle (doc 16 §9.5) : authentification, référentiel, mesures, seuils,
 * campagnes, matériel et export CSV. Pas de scénario d'IA : ces routes existent déjà côté API.
 * Les seuils restent des routes du socle : le service kit_parameters ne fait que les conseiller (doc 17).
 */
import { http, HttpResponse, type HttpHandler } from "msw";

import { canEditThresholds } from "@/lib/roles";
import { validateThresholds } from "@/lib/thresholds";
import type { Bucket, DeviceStatus } from "@/lib/types";

import { visibleDevice, visibleDeviceSeeds, visibleFarm, visibleFarms, visibleField } from "../access";
import { roleForCredentials, roleFromRefreshToken, tokenPair } from "../auth";
import { CORE_LATENCY_MS, DAY_MS, fail, iso, isoDay, notFound, ok, readJson, simulateLatency, url } from "../base";
import { deviceDetail, deviceView } from "../builders/device";
import { cropCyclesView, fieldDetail } from "../builders/field";
import { campaignsView, equipmentView, farmFields, kpiCsv } from "../builders/org";
import { lastSeen } from "../fixtures/places";
import { measurementRows } from "../fixtures/series";
import { coreRoute, dateParam, forbidden, intParam, invalid } from "../route";
import { effectiveThresholds, requestThresholds, thresholdState } from "../store";

import { isRecord, reportRequest } from "./params";

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 500;
const BUCKETS: readonly Bucket[] = ["raw", "1h", "1d", "1w", "1mo"];
const DEVICE_STATUSES: readonly DeviceStatus[] = ["active", "inactive", "retired"];

const isBucket = (value: string): value is Bucket => (BUCKETS as readonly string[]).includes(value);
const isDeviceStatus = (value: string): value is DeviceStatus => (DEVICE_STATUSES as readonly string[]).includes(value);

function stringField(body: unknown, key: string): string | null {
  if (!isRecord(body)) return null;
  const value = body[key];
  return typeof value === "string" && value !== "" ? value : null;
}

/** Liste paginée simple : `limit` borné, page unique (la simulation tient dans une page). */
function paged<T>(items: readonly T[], query: URLSearchParams): Response {
  const limit = intParam(query, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT);
  if (limit === null) return invalid(`« limit » entre 1 et ${MAX_LIMIT}.`);
  return ok(items.slice(0, limit), { total: items.length, page: 1, limit });
}

/* ---------- Authentification (avant toute session : pas de coreRoute) ---------- */

const authHandlers: HttpHandler[] = [
  http.post(url("/v1/auth/token"), async ({ request }) => {
    await simulateLatency(CORE_LATENCY_MS);
    const body = await readJson(request);
    const username = stringField(body, "username");
    const password = stringField(body, "password");
    if (!username || !password) return invalid("Identifiant et mot de passe obligatoires.");
    const role = roleForCredentials(username, password);
    return role ? ok(tokenPair(role)) : fail("INVALID_CREDENTIALS", "Identifiant ou mot de passe incorrect.", 401);
  }),
  http.post(url("/v1/auth/refresh"), async ({ request }) => {
    await simulateLatency(CORE_LATENCY_MS);
    const role = roleFromRefreshToken(stringField(await readJson(request), "refresh_token"));
    return role ? ok(tokenPair(role)) : fail("UNAUTHENTICATED", "Session expirée.", 401);
  }),
  http.post(url("/v1/auth/logout"), async () => {
    await simulateLatency(CORE_LATENCY_MS);
    return ok(null);
  }),
];

/* ---------- Référentiel ---------- */

const placeHandlers: HttpHandler[] = [
  coreRoute("get", "/v1/me", ({ user }) => ok(user.me)),
  coreRoute("get", "/v1/farms", ({ user, query }) => paged(visibleFarms(user), query)),
  coreRoute("get", "/v1/farms/:id/fields", ({ user, params }) => {
    const farm = visibleFarm(user, params.id ?? "");
    return farm ? ok(farmFields(farm)) : notFound();
  }),
  coreRoute("get", "/v1/fields/:id", ({ user, params, now }) => {
    const seed = visibleField(user, params.id ?? "");
    return seed ? ok(fieldDetail(seed, now)) : notFound();
  }),
  coreRoute("get", "/v1/fields/:id/crop-cycles", ({ user, params, now }) => {
    const seed = visibleField(user, params.id ?? "");
    return seed ? ok(cropCyclesView(seed, now)) : notFound();
  }),
  coreRoute("get", "/v1/campaigns", ({ user, query, now }) => paged(campaignsView(user, now), query)),
  coreRoute("get", "/v1/equipment", ({ user, query }) => paged(equipmentView(user), query)),
];

/* ---------- Kits, mesures et seuils ---------- */

const deviceHandlers: HttpHandler[] = [
  coreRoute("get", "/v1/devices", ({ user, query, now }) => {
    const status = query.get("status");
    if (status && !isDeviceStatus(status)) return invalid("Statut de kit inconnu.", { allowed: DEVICE_STATUSES });
    const seeds = visibleDeviceSeeds(user).filter((d) => !status || d.status === status);
    return paged(
      seeds.map((d) => deviceView(d, now)),
      query,
    );
  }),
  coreRoute("get", "/v1/devices/:id", ({ user, params, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    return seed ? ok(deviceDetail(seed, now)) : notFound();
  }),
  coreRoute("get", "/v1/devices/:id/measurements", ({ user, params, query, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    if (!seed) return notFound();
    const bucket = query.get("bucket") ?? "1h";
    if (!isBucket(bucket)) return fail("INVALID_BUCKET", "Pas d'agrégation inconnu.", 422, { details: { allowed: BUCKETS } });
    const to = query.has("to") ? dateParam(query, "to") : now;
    const from = query.has("from") ? dateParam(query, "from") : new Date(now.getTime() - DAY_MS);
    if (!from || !to) return invalid("Dates « from » ou « to » illisibles.");
    if (from.getTime() >= to.getTime()) return invalid("« from » doit précéder « to ».");
    const series = measurementRows(seed.id, effectiveThresholds(seed.id, now), bucket, from, to, lastSeen(seed, now));
    return ok(
      { device_id: seed.id, bucket, from: iso(from), to: iso(to), rows: series.rows },
      { count: series.rows.length, truncated: series.truncated },
    );
  }),
  coreRoute("get", "/v1/devices/:id/thresholds", ({ user, params, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    return seed ? ok(thresholdState(seed.id, now)) : notFound();
  }),
  coreRoute("put", "/v1/devices/:id/thresholds", async ({ request, user, params, now }) => {
    const seed = visibleDevice(user, params.id ?? "");
    if (!seed) return notFound();
    if (!canEditThresholds(user.me, seed.orgId)) return forbidden();
    const body = await readJson(request);
    const record = isRecord(body) ? body : {};
    const result = validateThresholds(record.start, record.stop);
    if (!result.ok) return fail("THRESHOLDS_INVALID", "Seuils invalides.", 400, { details: { errors: result.errors } });
    return ok(requestThresholds(seed.id, { start_pct: result.value.start, stop_pct: result.value.stop }, now));
  }),
];

/* ---------- Export CSV du rapport (même périmètre que /v1/reports/kpis) ---------- */

const reportHandlers: HttpHandler[] = [
  coreRoute("get", "/v1/reports/export.csv", ({ user, query, now }) => {
    const report = reportRequest(user, query, now);
    if (report instanceof Response) return report;
    const filename = `rapport-${report.scope.scope}-${isoDay(report.from)}-${isoDay(report.to)}.csv`;
    return new HttpResponse(kpiCsv(report.scope, report.from, report.to), {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  }),
];

export const coreHandlers: readonly HttpHandler[] = [...authHandlers, ...placeHandlers, ...deviceHandlers, ...reportHandlers];

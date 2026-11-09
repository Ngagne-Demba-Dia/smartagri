/**
 * Types partagés, calqués sur CONVENTIONS.md (§3 télémétrie, §5 API v1) et sur les vues du backend
 * (app/services/*_view). Toute évolution du contrat se fait d'abord dans CONVENTIONS.md.
 */

/* ---------- Enveloppe de réponse (CONVENTIONS §5) ---------- */

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/** `page/limit/total` pour les listes ; d'autres clés possibles (ex. mesures : count, truncated). */
export interface ApiMeta {
  page?: number;
  limit?: number;
  total?: number;
  [key: string]: unknown;
}

export interface Envelope<T> {
  success: boolean;
  data: T | null;
  error: ApiErrorBody | null;
  meta: ApiMeta | null;
}

/** Codes d'erreur métier connus du client (liste non exhaustive). */
export type ApiErrorCode =
  | "UNAUTHENTICATED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "THRESHOLDS_INVALID"
  | "MESSAGE_INVALID"
  | "INVALID_BUCKET"
  | "RATE_LIMITED"
  | "NETWORK_ERROR"
  | "BAD_RESPONSE"
  | (string & {});

/* ---------- Identité et rôles ---------- */

export type Role = "farmer" | "coop_manager" | "agronomist" | "admin";
export type OrgKind = "cooperative" | "farm" | "ngo" | "research" | "company";
export type AppLocale = "fr" | "wo" | "ff";

export interface Membership {
  organization_id: string;
  organization_name: string;
  organization_kind: OrgKind;
  role: Role;
}

export interface Me {
  id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  locale: AppLocale;
  memberships: Membership[];
}

/* ---------- Exploitations et parcelles ---------- */

export type IrrigationType = "drip" | "sprinkler" | "furrow" | "manual";

export interface Farm {
  id: string;
  organization_id: string;
  name: string;
  region: string | null;
  commune: string | null;
  latitude: number | null;
  longitude: number | null;
  area_ha: number | null;
  created_at: string;
}

export interface GeoJsonPolygon {
  type: "Polygon";
  coordinates: number[][][];
}

export interface Field {
  id: string;
  organization_id: string;
  farm_id: string;
  name: string;
  area_ha: number | null;
  soil_type: string | null;
  irrigation_type: IrrigationType | null;
  geometry: GeoJsonPolygon | null;
  centroid: { longitude: number; latitude: number } | null;
  created_at: string;
}

/* ---------- Kits, seuils, mesures ---------- */

export type DeviceStatus = "active" | "inactive" | "retired";
export type SyncStatus = "pending" | "sent" | "applied" | "failed";
export type TelemetrySource = "mqtt" | "relay" | "http";

export interface ThresholdPair {
  start_pct: number;
  stop_pct: number;
}

export interface ThresholdState {
  desired: ThresholdPair;
  reported: ThresholdPair | null;
  sync_status: SyncStatus;
  command_id: string | null;
  updated_at: string | null;
}

/** Clés canoniques de telemetry.v1 (CONVENTIONS §3) ; null = valeur absente ou hors plage plausible. */
export interface TelemetryMetrics {
  soil_moisture_pct: number | null;
  air_temp_c: number | null;
  air_humidity_pct: number | null;
  pressure_hpa: number | null;
  n_mgkg: number | null;
  p_mgkg: number | null;
  k_mgkg: number | null;
  pump_on: boolean | null;
  pump_fault: boolean | null;
  soil_sensor_ok: boolean | null;
  bme_ok: boolean | null;
  npk_ok: boolean | null;
  alert_fertilizer: boolean | null;
  alert_plant: boolean | null;
  threshold_start_pct: number | null;
  threshold_stop_pct: number | null;
}

export interface Measurement extends Partial<TelemetryMetrics> {
  ts: string;
  source: TelemetrySource;
  fw: string | null;
}

export interface Device {
  id: string;
  serial: string;
  name: string | null;
  organization_id: string;
  field_id: string | null;
  firmware_version: string | null;
  status: DeviceStatus;
  last_seen_at: string | null;
  thresholds: ThresholdState | null;
}

export interface DeviceDetail extends Device {
  latest_measurement: Measurement | null;
}

/** Agrégats : « {métrique}_{avg|min|max} » ; brut : clés canoniques. */
export type Bucket = "raw" | "1h" | "1d" | "1w" | "1mo";

export interface SeriesRow {
  ts: string;
  n_points?: number;
  soil_moisture_pct?: number | null;
  soil_moisture_pct_avg?: number | null;
  soil_moisture_pct_min?: number | null;
  soil_moisture_pct_max?: number | null;
  air_temp_c_avg?: number | null;
  pump_on_ratio?: number | null;
  [key: string]: unknown;
}

export interface MeasurementSeries {
  device_id: string;
  bucket: Bucket;
  from: string;
  to: string;
  rows: SeriesRow[];
}

export interface ThresholdsInput {
  start: number;
  stop: number;
}

/* ---------- Alertes ---------- */

export type AlertSeverity = "info" | "warning" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";

export interface Alert {
  id: string;
  organization_id: string;
  device_id: string | null;
  field_id: string | null;
  rule: string;
  severity: AlertSeverity;
  status: AlertStatus;
  message: string;
  details: Record<string, unknown> | null;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

/* ---------- Assistant ---------- */

export interface ChatInput {
  message: string;
  conversation_id?: string | null;
  organization_id?: string | null;
  locale?: AppLocale | null;
}

export interface ChatResult {
  conversation_id: string;
  reply: string;
  stop_reason: string | null;
  tools_used: string[];
  truncated: boolean;
  limit_reached: boolean;
  model: string | null;
  fallback_used: boolean;
}

/* ---------- Recommandations (services/recommendations.recommendation_view) ---------- */

export type RecommendationKind = "irrigation" | "fertilization";
export type IrrigationAction = "verifier_capteur" | "irriguer" | "surveiller" | "ne_pas_irriguer";
export type RecommendationFeedback = "followed" | "partially_followed" | "ignored" | "not_applicable";

export interface IrrigationAdvice {
  action: IrrigationAction;
  reason: string;
  etc_mm: number | null;
  net_mm: number | null;
  gross_mm: number | null;
  volume_m3: number | null;
  caveat: string;
}

export interface IrrigationPayload {
  advice: IrrigationAdvice;
  crop: string | null;
  et0_mm: number | null;
  et0_method: string | null;
  thresholds: { start_pct: number; stop_pct: number; source: string };
  measured_at: string | null;
  device_serial: string | null;
}

export interface NutrientStatus {
  nutrient: string;
  value: number | null;
  level: "bas" | "moyen" | "eleve" | null;
  message: string;
}

export interface FertilizationPayload {
  nutrients: NutrientStatus[];
  sensor_ok: boolean;
  caveat: string;
}

export type Recommendation =
  | { id: string; kind: "irrigation"; engine_version: string; created_at: string | null; payload: IrrigationPayload }
  | { id: string; kind: "fertilization"; engine_version: string; created_at: string | null; payload: FertilizationPayload };

/* ---------- Météo (services/weather.Forecast.as_dict) ---------- */

export interface WeatherDay {
  date: string;
  t_max_c: number | null;
  t_min_c: number | null;
  precipitation_mm: number | null;
  et0_mm: number | null;
  et0_hargreaves_mm: number | null;
}

export interface WeatherForecast {
  field_id: string;
  location_source: string;
  provider: string;
  latitude: number;
  longitude: number;
  fetched_at: string;
  source: "provider" | "cache" | "stale_cache";
  days: WeatherDay[];
}

/* ---------- Carte (services/farms.farm_map : FeatureCollection GeoJSON) ---------- */

export interface FieldFeatureProps {
  kind: "field";
  field_id: string;
  name: string;
  area_ha: number | null;
  crop: string | null;
  soil_moisture_pct: number | null;
  open_alerts: number;
}

export interface DeviceFeatureProps {
  kind: "device";
  device_id: string;
  serial: string;
  field_id: string | null;
  status: DeviceStatus;
  soil_moisture_pct: number | null;
  measured_at: string | null;
  last_seen_at: string | null;
  open_alerts: number;
  position_estimated: boolean;
}

export interface MapFeature<P> {
  type: "Feature";
  id: string;
  geometry: { type: string; coordinates: unknown } | null;
  properties: P;
}

/** Contour seul (couche field_boundary, doc 16 §9.3 n° 18). */
export interface BoundaryFeatureProps {
  kind: "boundary";
  field_id: string;
  area_ha: number | null;
}

export type MapFeatureProps = FieldFeatureProps | DeviceFeatureProps | BoundaryFeatureProps;

export interface FarmMap {
  type: "FeatureCollection";
  features: Array<MapFeature<MapFeatureProps>>;
}

/* ---------- Rapports (services/reports.build_report + kpis.compute_kpis) ---------- */

export interface Kpis {
  devices: number;
  fields: number;
  water_m3: number | null;
  devices_without_flow: number;
  pump_hours: number;
  irrigation_events: number;
  measurements: number;
  kit_uptime_pct: number | null;
  alerts_by_rule: Record<string, number>;
  diagnoses_by_label: Record<string, number>;
  recommendations_feedback: Partial<Record<RecommendationFeedback, number>>;
  recommendations_followed_pct: number | null;
}

export interface KpiReport {
  scope: "org" | "farm" | "field";
  scope_id: string;
  from: string;
  to: string;
  kpis: Kpis;
}

/* ---------- Modules V1.1+ (vues backend : equipment_view, campaign_view, cycle_view, yield_forecast) ---------- */

export type EquipmentKind = "pump" | "tank" | "solar_panel" | "battery" | "sensor" | "camera" | "gateway" | "other";
export type EquipmentStatus = "ok" | "maintenance" | "out_of_service";

export interface Equipment {
  id: string;
  organization_id: string;
  farm_id: string;
  kind: EquipmentKind;
  label: string;
  serial: string | null;
  installed_at: string | null;
  status: EquipmentStatus;
  device_id: string | null;
  flow_m3h: number | null;
  created_at: string;
}

export type CampaignStatus = "planned" | "active" | "closed";

export interface Campaign {
  id: string;
  organization_id: string;
  name: string;
  season: string; // TODO(contrat): valeurs de saison non figées dans CONVENTIONS (« dry » / « rainy » supposées)
  start_date: string;
  end_date: string;
  status: CampaignStatus;
  created_at: string;
}

export type CropCycleStatus = "planned" | "active" | "harvested" | "abandoned"; // TODO(contrat): liste supposée

export interface CropCycle {
  id: string;
  organization_id: string;
  field_id: string;
  campaign_id: string | null;
  crop: string;
  variety: string | null;
  planted_on: string | null;
  expected_harvest_on: string | null;
  harvested_on: string | null;
  yield_kg: number | null;
  status: CropCycleStatus;
  created_at: string;
}

/** GET /v1/fields/{id} : parcelle + cycle cultural actif (404 hors de l'organisation). */
export interface FieldDetail extends Field {
  active_cycle: CropCycle | null;
}

export interface YieldForecastRow {
  id: string;
  model_name: string;
  model_version: string;
  predicted_t_ha: number | null;
  p10: number | null;
  p90: number | null;
  created_at: string;
}

export interface YieldForecastView {
  field_id: string;
  crop_cycle: { id: string; crop: string; status: CropCycleStatus; planted_on: string | null };
  forecast: YieldForecastRow | null;
  actual_t_ha: number | null;
  caveat: string;
}

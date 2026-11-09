-- SmartAgri92 — extensions : campagnes, équipements et maintenance, cache météo,
-- prévisions de rendement, registre des modèles.
-- Confidentiel — réservé aux partenaires de travail.
-- Prérequis : 001_init.sql. Ré-exécutable. Même mode d'exécution que 001 (voir db/README.md).

-- ---------------------------------------------------------------------------------------------
-- 1. Campagnes (saison sèche / hivernage)
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS campaigns (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    name varchar(120) NOT NULL,
    season varchar(10) NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    status varchar(10) NOT NULL DEFAULT 'planned',
    CONSTRAINT ck_campaigns_season CHECK (season IN ('dry', 'rainy')),
    CONSTRAINT ck_campaigns_status CHECK (status IN ('planned', 'active', 'closed')),
    CONSTRAINT ck_campaigns_dates CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS ix_campaigns_organization_id ON campaigns (organization_id);

ALTER TABLE crop_cycles
    ADD COLUMN IF NOT EXISTS campaign_id uuid REFERENCES campaigns (id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_crop_cycles_campaign_id ON crop_cycles (campaign_id);

-- ---------------------------------------------------------------------------------------------
-- 2. Équipements et journal de maintenance
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    farm_id uuid NOT NULL REFERENCES farms (id) ON DELETE CASCADE,
    kind varchar(20) NOT NULL,
    label varchar(200) NOT NULL,
    serial varchar(100),
    installed_at date,
    status varchar(20) NOT NULL DEFAULT 'ok',
    device_id uuid REFERENCES devices (id) ON DELETE SET NULL,
    -- Débit nominal de la pompe (m³/h) : estimation des volumes d'irrigation à partir de pump_on.
    flow_m3h double precision,
    CONSTRAINT ck_equipment_kind CHECK (
        kind IN ('pump', 'tank', 'solar_panel', 'battery', 'sensor', 'camera', 'gateway', 'other')),
    CONSTRAINT ck_equipment_status CHECK (status IN ('ok', 'maintenance', 'out_of_service')),
    CONSTRAINT ck_equipment_flow CHECK (flow_m3h IS NULL OR flow_m3h > 0)
);
CREATE INDEX IF NOT EXISTS ix_equipment_organization_id ON equipment (organization_id);
CREATE INDEX IF NOT EXISTS ix_equipment_farm_id ON equipment (farm_id);
CREATE INDEX IF NOT EXISTS ix_equipment_device_id ON equipment (device_id);

CREATE TABLE IF NOT EXISTS maintenance_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    equipment_id uuid NOT NULL REFERENCES equipment (id) ON DELETE CASCADE,
    ts timestamptz NOT NULL,
    kind varchar(20) NOT NULL,
    notes text,
    cost_fcfa integer,
    created_by uuid REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT ck_maintenance_events_kind CHECK (
        kind IN ('inspection', 'preventive', 'corrective', 'replacement', 'other')),
    CONSTRAINT ck_maintenance_events_cost CHECK (cost_fcfa IS NULL OR cost_fcfa >= 0)
);
CREATE INDEX IF NOT EXISTS ix_maintenance_events_organization_id ON maintenance_events (organization_id);
CREATE INDEX IF NOT EXISTS ix_maintenance_events_equipment_ts ON maintenance_events (equipment_id, ts);

-- ---------------------------------------------------------------------------------------------
-- 3. Cache météo (Open-Meteo) — données publiques, pas de RLS
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_cache (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider varchar(40) NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    days integer NOT NULL,
    fetched_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    CONSTRAINT uq_weather_cache_key UNIQUE (provider, latitude, longitude, days)
);

-- ---------------------------------------------------------------------------------------------
-- 4. Prévisions de rendement et registre des modèles
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS yield_forecasts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    crop_cycle_id uuid NOT NULL REFERENCES crop_cycles (id) ON DELETE CASCADE,
    model_name varchar(100) NOT NULL,
    model_version varchar(64) NOT NULL,
    predicted_t_ha double precision NOT NULL,
    p10 double precision,
    p90 double precision,
    CONSTRAINT ck_yield_forecasts_predicted CHECK (predicted_t_ha >= 0),
    CONSTRAINT ck_yield_forecasts_p10 CHECK (p10 IS NULL OR p10 <= predicted_t_ha),
    CONSTRAINT ck_yield_forecasts_p90 CHECK (p90 IS NULL OR p90 >= predicted_t_ha)
);
CREATE INDEX IF NOT EXISTS ix_yield_forecasts_organization_id ON yield_forecasts (organization_id);
CREATE INDEX IF NOT EXISTS ix_yield_forecasts_cycle_created ON yield_forecasts (crop_cycle_id, created_at);

-- Modèles servis (paquets locaux joblib/ONNX vérifiés par SHA-256, ou exécutions OctOpus).
CREATE TABLE IF NOT EXISTS model_registry (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    name varchar(100) NOT NULL,
    version varchar(64) NOT NULL,
    stage varchar(12) NOT NULL DEFAULT 'none',
    uri varchar(1024) NOT NULL,
    sha256 varchar(64),
    source varchar(10) NOT NULL,
    octopus_run_id varchar(100),
    metrics jsonb,
    proof jsonb,
    features jsonb,
    CONSTRAINT uq_model_registry_name_version UNIQUE (name, version),
    CONSTRAINT ck_model_registry_stage CHECK (stage IN ('none', 'staging', 'production')),
    CONSTRAINT ck_model_registry_source CHECK (source IN ('octopus', 'agriml'))
);
-- Plusieurs versions peuvent être en production : l'API sert la plus récente (services/inference/registry.py).
CREATE INDEX IF NOT EXISTS ix_model_registry_name ON model_registry (name);

-- ---------------------------------------------------------------------------------------------
-- 5. RLS et droits des nouvelles tables
-- ---------------------------------------------------------------------------------------------
DO $$
DECLARE
    t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['campaigns', 'equipment', 'maintenance_events', 'yield_forecasts']
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
        EXECUTE format('CREATE POLICY tenant_isolation ON %I '
                       'USING (organization_id = ANY (app_current_org_ids())) '
                       'WITH CHECK (organization_id = ANY (app_current_org_ids()))', t);
    END LOOP;
END
$$;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON campaigns, equipment, maintenance_events, weather_cache, yield_forecasts, model_registry
    TO agri_app, agri_worker;
-- Le registre des modèles est alimenté par l'équipe ML (compte de migration), lu par l'API.
REVOKE INSERT, UPDATE, DELETE ON model_registry FROM agri_app;

-- SmartAgri92 — jeux de paramètres poussés aux kits (doc 16 § 6.1 et § 9.3, service 7 kit_parameters).
-- Confidentiel — réservé aux partenaires de travail.
-- Prérequis : 001_init.sql, 002_extensions.sql. Ré-exécutable.

CREATE TABLE IF NOT EXISTS device_parameter_sets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    organization_id uuid NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    device_id uuid NOT NULL REFERENCES devices (id) ON DELETE CASCADE,
    version integer NOT NULL,
    issued_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL,
    applied boolean NOT NULL DEFAULT false,
    applied_at timestamptz,
    CONSTRAINT uq_device_parameter_sets_device_version UNIQUE (device_id, version),
    CONSTRAINT ck_device_parameter_sets_version CHECK (version >= 1)
);
CREATE INDEX IF NOT EXISTS ix_device_parameter_sets_organization_id ON device_parameter_sets (organization_id);
CREATE INDEX IF NOT EXISTS ix_device_parameter_sets_device_version ON device_parameter_sets (device_id, version DESC);

DO $$
BEGIN
    EXECUTE 'ALTER TABLE device_parameter_sets ENABLE ROW LEVEL SECURITY';
    EXECUTE 'DROP POLICY IF EXISTS tenant_isolation ON device_parameter_sets';
    EXECUTE 'CREATE POLICY tenant_isolation ON device_parameter_sets '
            'USING (organization_id = ANY (app_current_org_ids())) '
            'WITH CHECK (organization_id = ANY (app_current_org_ids()))';
END
$$;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON device_parameter_sets
    TO agri_app, agri_worker;

-- CIVIC WATCH 0001: review-gated historical records.
-- Apply manually with psql -v ON_ERROR_STOP=1 -f migrations/0001_records.sql
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS schema_migrations (
 version text PRIMARY KEY,
 applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS records (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 title text NOT NULL CHECK (length(trim(title)) > 0),
 description text NOT NULL DEFAULT '',
 category text NOT NULL CHECK (category IN ('police','immigration','surveillance','other')),
 occurred_at timestamptz,
 public_location_label text,
 internal_notes text NOT NULL DEFAULT '',
 verification_status text NOT NULL DEFAULT 'unverified'
   CHECK (verification_status IN ('unverified','source_authenticated','verified','disputed')),
 publication_status text NOT NULL DEFAULT 'draft'
   CHECK (publication_status IN ('draft','in_review','approved','published','withdrawn')),
 sensitive boolean NOT NULL DEFAULT true,
 reviewed_by text,
 reviewed_at timestamptz,
 published_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT published_requires_review CHECK (
   publication_status <> 'published' OR (
     verification_status = 'verified' AND sensitive = false AND
     reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND published_at IS NOT NULL
   )
 )
);
CREATE INDEX IF NOT EXISTS records_public_idx ON records(published_at DESC, id DESC)
 WHERE publication_status='published' AND verification_status='verified' AND sensitive=false;
CREATE TABLE IF NOT EXISTS record_sources (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 incident_id uuid NOT NULL REFERENCES records(id) ON DELETE RESTRICT,
 source_type text NOT NULL CHECK (source_type IN ('official_record','court_record','news','research','other')),
 source_title text NOT NULL,
 source_url text NOT NULL CHECK (source_url ~* '^https://'),
 published_at timestamptz,
 reviewed boolean NOT NULL DEFAULT false,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS record_sources_incident_idx ON record_sources(incident_id);
CREATE TABLE IF NOT EXISTS audit_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 record_id uuid REFERENCES records(id),
 actor text NOT NULL,
 action text NOT NULL,
 details jsonb NOT NULL DEFAULT '{}'::jsonb,
 occurred_at timestamptz NOT NULL DEFAULT now()
);
-- Explicit field projection prevents accidental exposure of private notes or geometry.
CREATE OR REPLACE VIEW public_incidents AS
SELECT r.id, r.title, r.description, r.category, r.occurred_at,
       r.published_at, r.verification_status, r.public_location_label,
       (SELECT count(*)::int FROM record_sources s
        WHERE s.incident_id = r.id AND s.reviewed = true) AS source_count
FROM records r
WHERE r.publication_status = 'published'
  AND r.verification_status = 'verified'
  AND r.sensitive = false
  AND EXISTS (SELECT 1 FROM record_sources s WHERE s.incident_id = r.id AND s.reviewed = true);
CREATE OR REPLACE VIEW public_sources AS
SELECT s.incident_id, s.source_type, s.source_title, s.source_url, s.published_at
FROM record_sources s JOIN public_incidents r ON r.id = s.incident_id
WHERE s.reviewed = true;
INSERT INTO schema_migrations(version) VALUES ('0001') ON CONFLICT DO NOTHING;
COMMIT;

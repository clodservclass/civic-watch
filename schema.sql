CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS incidents (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 title text NOT NULL,
 description text NOT NULL DEFAULT '',
 category text NOT NULL DEFAULT 'other',
 status text NOT NULL DEFAULT 'unverified' CHECK (status IN ('unverified','source_authenticated','verified','disputed')),
 occurred_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 geom geometry(Point,4326),
 source_url text,
 source_type text NOT NULL DEFAULT 'community'
);
CREATE INDEX IF NOT EXISTS incidents_geom_idx ON incidents USING gist(geom);
CREATE TABLE IF NOT EXISTS evidence (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 incident_id uuid REFERENCES incidents(id),
 sha256 char(64) NOT NULL,
 storage_key text NOT NULL,
 visibility text NOT NULL DEFAULT 'private'
);
CREATE TABLE IF NOT EXISTS audit_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor text NOT NULL,
 action text NOT NULL,
 entity_id text NOT NULL,
 occurred_at timestamptz NOT NULL DEFAULT now(),
 details jsonb NOT NULL DEFAULT '{}'::jsonb
);

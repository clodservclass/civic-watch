-- CIVIC WATCH 0002: source-gated surveillance program registry
BEGIN;
CREATE TABLE IF NOT EXISTS surveillance_programs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 agency_name text NOT NULL CHECK(length(trim(agency_name))>0),
 program_name text NOT NULL CHECK(length(trim(program_name))>0),
 technology text NOT NULL CHECK(technology IN ('alpr','cctv','facial_recognition','drones','analytics','other')),
 jurisdiction text NOT NULL DEFAULT '',
 vendor_name text,
 description text NOT NULL DEFAULT '',
 retention_policy text,
 sharing_policy text,
 contract_amount_usd numeric(14,2) CHECK(contract_amount_usd IS NULL OR contract_amount_usd >= 0),
 policy_notes text NOT NULL DEFAULT '',
 review_status text NOT NULL DEFAULT 'draft'
   CHECK(review_status IN ('draft','in_review','verified','disputed','withdrawn')),
 public_status text NOT NULL DEFAULT 'unpublished'
   CHECK(public_status IN ('unpublished','published','withdrawn')),
 sensitive boolean NOT NULL DEFAULT true,
 reviewed_by text,
 reviewed_at timestamptz,
 published_at timestamptz,
 updated_at timestamptz NOT NULL DEFAULT now(),
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT surveillance_publish_gate CHECK(public_status <> 'published' OR
   (review_status='verified' AND sensitive=false AND reviewed_by IS NOT NULL
    AND reviewed_at IS NOT NULL AND published_at IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS surveillance_sources (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 program_id uuid NOT NULL REFERENCES surveillance_programs(id) ON DELETE RESTRICT,
 source_title text NOT NULL CHECK(length(trim(source_title))>0),
 source_url text NOT NULL CHECK(source_url ~* '^https://'),
 source_type text NOT NULL CHECK(source_type IN ('official_record','contract','policy','court_record','news','research','other')),
 document_date date,
 verified boolean NOT NULL DEFAULT false,
 reviewed_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 CONSTRAINT source_verified_review CHECK(NOT verified OR reviewed_at IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS surveillance_sources_program_idx ON surveillance_sources(program_id);
CREATE INDEX IF NOT EXISTS surveillance_programs_public_idx ON surveillance_programs(published_at DESC, id DESC)
 WHERE public_status='published' AND review_status='verified' AND sensitive=false;
CREATE OR REPLACE VIEW public_surveillance_programs AS
SELECT p.id, p.agency_name, p.program_name, p.technology, p.jurisdiction,
 p.vendor_name, p.description, p.retention_policy, p.sharing_policy,
 p.contract_amount_usd, p.published_at,
 (SELECT count(*)::int FROM surveillance_sources s WHERE s.program_id=p.id AND s.verified=true) AS source_count
FROM surveillance_programs p
WHERE p.public_status='published' AND p.review_status='verified' AND p.sensitive=false
AND EXISTS(SELECT 1 FROM surveillance_sources s WHERE s.program_id=p.id AND s.verified=true);
CREATE OR REPLACE VIEW public_surveillance_sources AS
SELECT s.program_id,s.source_title,s.source_url,s.source_type,s.document_date
FROM surveillance_sources s JOIN public_surveillance_programs p ON p.id=s.program_id
WHERE s.verified=true;
INSERT INTO schema_migrations(version) VALUES ('0002') ON CONFLICT DO NOTHING;
COMMIT;

-- Project workspace schema migration

-- 0) Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Helper to expose unaccent() as an immutable function so it can be used in
-- generated columns and expression indexes.
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
RETURNS NULL ON NULL INPUT
AS $$
  SELECT unaccent($1);
$$;

-- 1) Enum types
DO $$ BEGIN
  CREATE TYPE permission_role AS ENUM ('owner','maintainer','editor','commenter','viewer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE sensitivity_level AS ENUM ('public','internal','restricted','secret');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE share_mode AS ENUM ('private','org','link','domain');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE principal_type AS ENUM ('user','org','domain','group','link');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE resource_type AS ENUM ('project','file','document','memory','instruction','chat','snapshot');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 2) Organizations, projects, and memberships
CREATE TABLE IF NOT EXISTS organizations (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name            text NOT NULL,
  status          text NOT NULL DEFAULT 'active',
  visibility      text NOT NULL DEFAULT 'private',
  budget_quota    bigint,
  current_instr_v integer,
  created_by      uuid NOT NULL REFERENCES auth.users(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS project_members (
  project_id    uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id       uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role          permission_role NOT NULL,
  invited_by    uuid REFERENCES auth.users(id),
  created_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members(user_id);

-- 3) Instructions and memories
CREATE TABLE IF NOT EXISTS instructions (
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  version      integer NOT NULL,
  content      text NOT NULL,
  created_by   uuid NOT NULL REFERENCES auth.users(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, version)
);

CREATE TABLE IF NOT EXISTS memories (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  k            text NOT NULL,
  v            jsonb NOT NULL,
  source       text,
  expires_at   timestamptz,
  confidence   real,
  created_by   uuid NOT NULL REFERENCES auth.users(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, k)
);

-- 4) Files, documents, and chunks
CREATE TABLE IF NOT EXISTS files (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  r2_key       text NOT NULL,
  name         text NOT NULL,
  mime         text,
  size_bytes   bigint,
  version      integer NOT NULL DEFAULT 1,
  sensitivity  sensitivity_level NOT NULL DEFAULT 'internal',
  checksum     text,
  created_by   uuid NOT NULL REFERENCES auth.users(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE(project_id, r2_key, version)
);

CREATE TABLE IF NOT EXISTS documents (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  file_id      uuid NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  title        text,
  page_count   integer,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_chunks (
  id           bigserial PRIMARY KEY,
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page         integer,
  heading      text,
  body         text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE document_chunks
  ADD COLUMN IF NOT EXISTS tsv tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple', immutable_unaccent(coalesce(heading, '') || ' ' || coalesce(body, '')))
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_document_chunks_project ON document_chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_tsv ON document_chunks USING GIN(tsv);
CREATE INDEX IF NOT EXISTS idx_document_chunks_trgm_heading ON document_chunks USING GIN(heading gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_document_chunks_trgm_body    ON document_chunks USING GIN(body gin_trgm_ops);

-- 5) Sharing and permissions
CREATE TABLE IF NOT EXISTS permissions (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id     uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  principal_type principal_type NOT NULL,
  principal_id   text,
  role           permission_role NOT NULL,
  created_by     uuid NOT NULL REFERENCES auth.users(id),
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_permissions_project ON permissions(project_id);

CREATE TABLE IF NOT EXISTS share_links (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  token        text NOT NULL UNIQUE,
  mode         share_mode NOT NULL,
  domains      text[] DEFAULT '{}',
  expires_at   timestamptz,
  max_uses     integer,
  used_count   integer NOT NULL DEFAULT 0,
  created_by   uuid NOT NULL REFERENCES auth.users(id),
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- 6) Redaction rules and runs
CREATE TABLE IF NOT EXISTS redaction_rules (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name         text NOT NULL,
  pattern      text NOT NULL,
  replacement  text NOT NULL,
  scope        text NOT NULL DEFAULT 'all',
  enabled      boolean NOT NULL DEFAULT true,
  created_by   uuid NOT NULL REFERENCES auth.users(id),
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS redaction_runs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  input_type   text NOT NULL,
  input_ref    text,
  status       text NOT NULL DEFAULT 'queued',
  stats        jsonb,
  created_by   uuid NOT NULL REFERENCES auth.users(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  finished_at  timestamptz
);

CREATE TABLE IF NOT EXISTS redaction_run_items (
  run_id       uuid NOT NULL REFERENCES redaction_runs(id) ON DELETE CASCADE,
  rule_id      uuid NOT NULL REFERENCES redaction_rules(id) ON DELETE CASCADE,
  target_ref   text,
  count        integer,
  PRIMARY KEY (run_id, rule_id, target_ref)
);

-- 7) Snapshots
CREATE TABLE IF NOT EXISTS snapshots (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name            text,
  instruction_ver integer,
  created_by      uuid NOT NULL REFERENCES auth.users(id),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS snapshot_files (
  snapshot_id   uuid NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
  file_id       uuid NOT NULL REFERENCES files(id),
  file_version  integer NOT NULL,
  PRIMARY KEY (snapshot_id, file_id, file_version)
);

-- 8) Project to chats mapping
CREATE TABLE IF NOT EXISTS project_chats (
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chat_id      uuid NOT NULL,
  added_by     uuid NOT NULL REFERENCES auth.users(id),
  added_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, chat_id)
);

-- 9) Audit and usage tracking
CREATE TABLE IF NOT EXISTS audit_logs (
  id            bigserial PRIMARY KEY,
  at            timestamptz NOT NULL DEFAULT now(),
  actor_user_id uuid,
  org_id        uuid,
  project_id    uuid,
  action        text NOT NULL,
  resource_type resource_type,
  resource_id   text,
  ip            inet,
  user_agent    text,
  meta          jsonb
);
CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_logs(project_id, at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action  ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_meta    ON audit_logs USING GIN(meta jsonb_path_ops);

CREATE TABLE IF NOT EXISTS project_budgets (
  project_id   uuid PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  period       text NOT NULL DEFAULT 'monthly',
  token_limit  bigint,
  hardcap      boolean NOT NULL DEFAULT false,
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS usage_ledger (
  id           bigserial PRIMARY KEY,
  at           timestamptz NOT NULL DEFAULT now(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chat_id      uuid,
  kind         text NOT NULL,
  tokens_in    bigint DEFAULT 0,
  tokens_out   bigint DEFAULT 0,
  cost_cents   integer DEFAULT 0,
  meta         jsonb
);
CREATE INDEX IF NOT EXISTS idx_usage_project_at ON usage_ledger(project_id, at DESC);

-- 10) Search view
CREATE OR REPLACE VIEW v_project_search AS
SELECT
  c.project_id,
  c.document_id,
  c.page,
  ts_rank_cd(c.tsv, websearch_to_tsquery('simple', unaccent(coalesce($$q$$, '')))) AS rank,
  left(c.body, 500) AS snippet
FROM document_chunks c;

-- 11) RLS skeleton (policies to be refined per project requirements)
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY projects_select
ON projects FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM project_members m
    WHERE m.project_id = projects.id
      AND m.user_id = auth.uid()
  )
);

CREATE POLICY projects_insert
ON projects FOR INSERT
WITH CHECK ( created_by = auth.uid() );

CREATE POLICY projects_update
ON projects FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM project_members m
    WHERE m.project_id = projects.id
      AND m.user_id = auth.uid()
      AND m.role IN ('owner', 'maintainer')
  )
);

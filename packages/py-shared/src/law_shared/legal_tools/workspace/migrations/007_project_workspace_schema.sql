-- Project workspace schema migration (revised)

-- Reset legacy search view before dropping dependent tables
DROP VIEW IF EXISTS v_project_search;

-- Drop legacy tables that are no longer part of the workspace schema
DROP TABLE IF EXISTS usage_ledger CASCADE;
DROP TABLE IF EXISTS project_budgets CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS project_chats CASCADE;
DROP TABLE IF EXISTS snapshot_files CASCADE;
DROP TABLE IF EXISTS snapshots CASCADE;
DROP TABLE IF EXISTS redaction_run_items CASCADE;
DROP TABLE IF EXISTS redaction_runs CASCADE;
DROP TABLE IF EXISTS redaction_rules CASCADE;
DROP TABLE IF EXISTS share_links CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS memories CASCADE;
DROP TABLE IF EXISTS instructions CASCADE;
DROP TABLE IF EXISTS project_members CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS project_update_files CASCADE;
DROP TABLE IF EXISTS updates CASCADE;

-- Drop enum types introduced by the previous schema
DROP TYPE IF EXISTS permission_role CASCADE;
DROP TYPE IF EXISTS sensitivity_level CASCADE;
DROP TYPE IF EXISTS share_mode CASCADE;
DROP TYPE IF EXISTS principal_type CASCADE;
DROP TYPE IF EXISTS resource_type CASCADE;

-- Recreate enums required by the application models
DO $$
BEGIN
    CREATE TYPE permission_role AS ENUM ('owner', 'maintainer', 'editor', 'commenter', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- Ensure required extensions exist
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Core organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    created_by  uuid NOT NULL
);

-- Workspace projects
CREATE TABLE IF NOT EXISTS projects (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       uuid,
    name         text NOT NULL,
    status       text,
    created_by   uuid NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    description  text,
    archived     boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS projects_index_0
    ON projects (created_by, updated_at);

-- Memberships between projects and users
CREATE TABLE IF NOT EXISTS project_members (
    project_id  uuid NOT NULL,
    user_id     uuid NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    invited_by  uuid,
    role        permission_role NOT NULL,
    PRIMARY KEY (project_id, user_id)
);

-- Project update file metadata
CREATE TABLE IF NOT EXISTS project_update_files (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket        text NOT NULL DEFAULT 'lawai-prod',
    object_key    text NOT NULL,
    version_id    text,
    etag          text,
    sha256_hex    text,
    is_public     boolean NOT NULL DEFAULT false,
    content_disp  text,
    deleted_at    timestamptz,
    cdn_path      text
);

-- Project updates
CREATE TABLE IF NOT EXISTS updates (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id             uuid,
    created_by             uuid,
    body                   text,
    created_at             timestamptz DEFAULT now(),
    project_update_file_id uuid
);

CREATE INDEX IF NOT EXISTS updates_index_0
    ON updates (created_at);

-- Project instructions (single active version per project)
CREATE TABLE IF NOT EXISTS instructions (
    project_id  uuid NOT NULL,
    version     integer NOT NULL,
    content     text NOT NULL,
    created_by  uuid NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    tsv         tsvector,
    PRIMARY KEY (project_id, version)
);

-- Foreign key relationships
ALTER TABLE projects
    ADD CONSTRAINT projects_org_id_fkey
    FOREIGN KEY (org_id) REFERENCES organizations(id)
    ON UPDATE NO ACTION ON DELETE NO ACTION;

ALTER TABLE project_members
    ADD CONSTRAINT project_members_project_id_fkey
    FOREIGN KEY (project_id) REFERENCES projects(id)
    ON UPDATE NO ACTION ON DELETE CASCADE;

ALTER TABLE updates
    ADD CONSTRAINT updates_project_id_fkey
    FOREIGN KEY (project_id) REFERENCES projects(id)
    ON UPDATE NO ACTION ON DELETE CASCADE;

ALTER TABLE updates
    ADD CONSTRAINT updates_project_update_file_id_fkey
    FOREIGN KEY (project_update_file_id) REFERENCES project_update_files(id)
    ON UPDATE NO ACTION ON DELETE SET NULL;

ALTER TABLE instructions
    ADD CONSTRAINT instructions_project_id_fkey
    FOREIGN KEY (project_id) REFERENCES projects(id)
    ON UPDATE NO ACTION ON DELETE CASCADE;

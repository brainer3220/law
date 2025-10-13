-- Migration: Remove auth.users foreign key constraints
-- Date: 2025-10-10

BEGIN;

-- Drop foreign key constraints to auth.users
ALTER TABLE projects
DROP CONSTRAINT IF EXISTS projects_created_by_fkey;

ALTER TABLE project_members
DROP CONSTRAINT IF EXISTS project_members_user_id_fkey,
DROP CONSTRAINT IF EXISTS project_members_invited_by_fkey;

ALTER TABLE project_chats
DROP CONSTRAINT IF EXISTS project_chats_added_by_fkey;

ALTER TABLE instructions
DROP CONSTRAINT IF EXISTS instructions_created_by_fkey;

ALTER TABLE memories
DROP CONSTRAINT IF EXISTS memories_created_by_fkey;

ALTER TABLE files
DROP CONSTRAINT IF EXISTS files_created_by_fkey;

ALTER TABLE permissions
DROP CONSTRAINT IF EXISTS permissions_created_by_fkey;

ALTER TABLE share_links
DROP CONSTRAINT IF EXISTS share_links_created_by_fkey;

ALTER TABLE redaction_rules
DROP CONSTRAINT IF EXISTS redaction_rules_created_by_fkey;

ALTER TABLE redaction_runs
DROP CONSTRAINT IF EXISTS redaction_runs_created_by_fkey;

ALTER TABLE snapshots
DROP CONSTRAINT IF EXISTS snapshots_created_by_fkey;

COMMIT;

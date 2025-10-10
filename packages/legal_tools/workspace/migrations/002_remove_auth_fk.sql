-- Migration: Remove auth.users foreign key constraints
-- Date: 2025-10-10

BEGIN;

-- Drop foreign key constraints to auth.users
ALTER TABLE projects
DROP CONSTRAINT IF EXISTS projects_created_by_fkey;

ALTER TABLE project_members
DROP CONSTRAINT IF EXISTS project_members_user_id_fkey,
DROP CONSTRAINT IF EXISTS project_members_invited_by_fkey;

COMMIT;

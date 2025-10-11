-- Migration: Add archived and description columns to projects table
-- Date: 2025-10-10

BEGIN;

-- Add description column
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS description TEXT;

-- Add archived column with default false
ALTER TABLE projects
ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT false;

-- Create index for archived queries
CREATE INDEX IF NOT EXISTS idx_projects_archived ON projects(archived);

COMMIT;

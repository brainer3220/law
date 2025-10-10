-- Migration: Restructure project_chats table
-- Date: 2025-10-11
-- Description: Changes project_chats from composite PK (project_id, chat_id) 
--              to single PK (id), making it a proper chat entity table

BEGIN;

-- Drop the old table and recreate with new structure
DROP TABLE IF EXISTS project_chats CASCADE;

CREATE TABLE project_chats (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title        text NOT NULL DEFAULT 'New Chat',
  created_by   uuid NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  added_by     uuid NOT NULL
);

-- Create index on project_id for faster lookups
CREATE INDEX idx_project_chats_project_id ON project_chats(project_id);

-- Create trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_project_chats_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS project_chats_updated_at_trigger ON project_chats;
CREATE TRIGGER project_chats_updated_at_trigger
  BEFORE UPDATE ON project_chats
  FOR EACH ROW
  EXECUTE FUNCTION update_project_chats_updated_at();

COMMIT;

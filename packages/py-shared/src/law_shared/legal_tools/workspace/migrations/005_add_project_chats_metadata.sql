-- Migration: Add metadata fields to project_chats table
-- Date: 2025-10-11
-- Description: Adds title, created_by, created_at, updated_at fields to project_chats
--              and makes chat_id auto-generated

BEGIN;

-- Add title column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'project_chats'
    AND column_name = 'title'
  ) THEN
    ALTER TABLE project_chats
    ADD COLUMN title text NOT NULL DEFAULT 'New Chat';
  END IF;
END $$;

-- Add created_by column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'project_chats'
    AND column_name = 'created_by'
  ) THEN
    ALTER TABLE project_chats
    ADD COLUMN created_by uuid NOT NULL DEFAULT gen_random_uuid();
  END IF;
END $$;

-- Add created_at column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'project_chats'
    AND column_name = 'created_at'
  ) THEN
    ALTER TABLE project_chats
    ADD COLUMN created_at timestamptz NOT NULL DEFAULT now();
  END IF;
END $$;

-- Add updated_at column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'project_chats'
    AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE project_chats
    ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
  END IF;
END $$;

-- Make chat_id auto-generate if no value is provided
-- Note: We'll set a default for new rows, but existing rows keep their values
ALTER TABLE project_chats
ALTER COLUMN chat_id SET DEFAULT gen_random_uuid();

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

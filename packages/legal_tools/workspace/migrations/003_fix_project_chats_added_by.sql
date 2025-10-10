-- Migration: Fix project_chats.added_by column
-- Date: 2025-10-11
-- Issue: Column project_chats.added_by was missing or had constraint issues

BEGIN;

-- Ensure the project_chats table exists
CREATE TABLE IF NOT EXISTS project_chats (
  project_id   uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  chat_id      uuid NOT NULL,
  added_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (project_id, chat_id)
);

-- Add the added_by column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'project_chats'
    AND column_name = 'added_by'
  ) THEN
    ALTER TABLE project_chats
    ADD COLUMN added_by uuid NOT NULL DEFAULT gen_random_uuid();
  END IF;
END $$;

-- Drop the foreign key constraint to auth.users if it exists
ALTER TABLE project_chats
DROP CONSTRAINT IF EXISTS project_chats_added_by_fkey;

-- Ensure the column is NOT NULL
ALTER TABLE project_chats
ALTER COLUMN added_by SET NOT NULL;

COMMIT;

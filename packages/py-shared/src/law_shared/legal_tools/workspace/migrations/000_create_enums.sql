-- Migration: Create workspace enum types
-- Date: 2025-10-10

BEGIN;

-- Create permission_role enum
DO $$ BEGIN
  CREATE TYPE permission_role AS ENUM ('owner', 'maintainer', 'editor', 'commenter', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMIT;

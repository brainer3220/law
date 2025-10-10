-- Migration: Create workspace enum types
-- Date: 2025-10-10

BEGIN;

-- Create permission_role enum
DO $$ BEGIN
  CREATE TYPE permission_role AS ENUM ('owner', 'maintainer', 'editor', 'commenter', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Create sensitivity_level enum
DO $$ BEGIN
  CREATE TYPE sensitivity_level AS ENUM ('public', 'internal', 'restricted', 'secret');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Create share_mode enum
DO $$ BEGIN
  CREATE TYPE share_mode AS ENUM ('private', 'org', 'link', 'domain');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Create principal_type enum
DO $$ BEGIN
  CREATE TYPE principal_type AS ENUM ('user', 'org', 'domain', 'group', 'link');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Create resource_type enum
DO $$ BEGIN
  CREATE TYPE resource_type AS ENUM ('project', 'file', 'document', 'memory', 'instruction', 'chat', 'snapshot');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

COMMIT;

-- Migration: Create helper functions for full-text search

-- Create immutable unaccent function for use in generated columns
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE STRICT
AS $$
    SELECT $1;  -- Simple pass-through for now, can be enhanced with unaccent extension
$$;

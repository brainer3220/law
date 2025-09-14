-- Enable required extensions (run in Supabase SQL editor)
-- ParadeDB BM25 (pg_search) must be available on the instance.
-- If unavailable, contact Supabase support to enable or use PGroonga/RUM fallback.

-- Optional but recommended for UUIDs and JSON utils
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ParadeDB full-text search (BM25)
CREATE EXTENSION IF NOT EXISTS pg_search;

-- Application schema
CREATE TABLE IF NOT EXISTS public.legal_docs (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  doc_id       text UNIQUE,
  title        text,
  body         text,
  meta         jsonb,
  path         text,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- BM25 index optimized for Korean/legal text
-- Use ICU tokenizer for broad Unicode; switch to ngram if partial matching is needed.
CREATE INDEX IF NOT EXISTS legal_docs_bm25_idx
ON public.legal_docs
USING bm25 (id, title, body)
WITH (
  key_field='id',
  text_fields='{
    "title": {"tokenizer": {"type": "icu"}},
    "body":  {"tokenizer": {"type": "icu"}}
  }'
);

-- Example query (BM25 scoring)
-- SELECT id, title, paradedb.score(id) AS score
-- FROM public.legal_docs
-- WHERE title @@@ $1 OR body @@@ $1
-- ORDER BY score DESC
-- LIMIT 10;


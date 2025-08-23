Law MVP CLI
=================

Simple command-line tool to explore the legal JSON dataset in `data/`.

Usage
-----
- Search by keyword (indexed, fast): `uv run main.py search "주40시간제" --limit 5`
- Preview a file: `uv run main.py preview "data/.../민사법_유권해석_요약_518.json"`
- Show stats: `uv run main.py stats`
- Force rebuild index: `uv run main.py reindex`

Supabase/Postgres
-----------------
- Configure env var: set `SUPABASE_DB_URL` (or `DATABASE_URL`) to your Supabase Postgres connection string. Use a service role key for ingest from local.
- Environment variables are loaded automatically from a `.env` file when the CLI starts.
- Example DSN: `postgresql://brainer.iptime.org:5432/postgres?user=postgres.your-tenant-id&password=your-super-secret-and-long-postgres-password`
- Install deps: `uv venv && uv sync` (adds `duckdb`, `psycopg`)
- Ingest JSON into Supabase: `uv run main.py ingest-supabase --batch 500`
- Search via Supabase: `uv run main.py search-supabase "주40시간제" --limit 10`
- You can also pass a DSN directly: `uv run main.py ingest-supabase --dsn "postgresql://..."`

Schema notes
- Table `records` is created automatically with columns mirroring the JSON fields and a `full_text` column.
- If permitted, an FTS `tsvector` column and GIN index are created; otherwise a trigram index on `full_text` is attempted. Fallback is ILIKE search.

Tips
- If your password contains special characters, URL-encode them in the DSN or use env vars.
- Some providers require `?sslmode=require`; include it in the DSN if needed.

Notes
-----
- Search now uses a persistent DuckDB index stored at `data/records.duckdb` for speed. Files are incrementally reindexed when their mtime changes.
- DuckDB (`duckdb` Python package) is required. If missing, install via UV.
- When introducing additional libraries later, check usage via Context7 per project guidance.

UV Workflow
-----------
- Create a venv and sync: `uv venv && uv sync` (installs `duckdb`)
- Run without installing: `uv run main.py search "주40시간제" --limit 5`
- Install console script: `uv pip install -e .` then use `law search "주40시간제"`
- Alternative run: `uv run law stats` (after editable install)

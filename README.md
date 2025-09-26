Law CLI
=======

Command-line tool to explore the legal JSON dataset in `data/` and query a Meilisearch-backed keyword index.

Usage
-----
- Preview a file: `uv run main.py preview "data/.../민사법_유권해석_요약_518.json"`
- Show stats: `uv run main.py stats`
- Search Meilisearch index: `uv run main.py meili-search "가산금 면제" --limit 5`
- Agentic ask (LangGraph over Meilisearch): `uv run main.py ask "근로시간 면제업무 관련 판례 알려줘" --k 5 --max-iters 3`
- Serve OpenAI-compatible API: `uv run main.py serve --host 127.0.0.1 --port 8080`

OpenAI-Compatible API (Streaming)
---------------------------------
Run the server:
```
uv run main.py serve --host 127.0.0.1 --port 8080
```

Chat Completions (non-streaming):
```
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5-mini-2025-08-07",
    "messages": [{"role":"user","content":"근로시간 면제업무 관련 판례 알려줘"}],
    "stream": false,
    "top_k": 5,
    "max_iters": 3
  }'
```

Streaming responses (SSE-like, compatible with OpenAI clients using `stream: true`):
```
curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-5-mini-2025-08-07",
    "messages": [{"role":"user","content":"근로시간 면제업무 관련 판례 알려줘"}],
    "stream": true
  }'
```
Notes:
- Set `LAW_DATA_DIR` to point to your data folder if not `./data`.
- The server runs the same LangGraph agent as the CLI and streams the final answer in chunks.

Supabase/Postgres (optional; BM25 FTS)
-------------------------------------
Enable PostgreSQL-backed full-text search using ParadeDB BM25. This is optional; DuckDB remains default.

1) Install optional dependency:
```
uv pip install psycopg[binary]
```

2) Set DSN for Supabase Postgres:
```
export SUPABASE_DB_URL='postgresql://postgres.your-tenant-id:your-super-secret-and-long-postgres-password@brainer.iptime.org:5432/postgres?sslmode=disable'
# or: export PG_DSN=...
```

3) Initialize schema + BM25 index:
```
uv run main.py pg-init
```

4) Load local JSON to Postgres:
```
 uv run main.py pg-load --data-dir data
```

5) Search with BM25:
```
uv run main.py pg-search "근로시간 면제" --limit 5
```

Notes:
- Instance must have ParadeDB `pg_search` extension enabled. If not, request enablement or consider PGroonga/RUM (non-BM25) alternatives.

Meilisearch search & ingestion
------------------------------
You can index the bundled sample documents into a running Meilisearch instance (default URL: `http://localhost:7700`) and query them via CLI or Python.

1) Start Meilisearch locally (Docker example):
```
docker run -it --rm -p 7700:7700 getmeili/meilisearch:v1.9.0
```

2) Load the sample legal guidance files:
```
uv run main.py meili-load --data-dir data/meilisearch
```

3) Query from the CLI:
```
uv run main.py meili-search "가산금 면제" --limit 5
```

4) Query from Python:
```python
from packages.legal_tools.meili_search import search_meilisearch

for hit in search_meilisearch("가산금 면제"):
    print(hit.title, hit.snippet)
```

Environment variables:
- `MEILI_URL` / `MEILI_HTTP_ADDR` — override the base URL.
- `MEILI_MASTER_KEY` / `MEILI_API_KEY` — supply an API key when security is enabled.
- `MEILI_INDEX` — change the target index (defaults to `legal-docs`).


Notes
-----
- Search now uses Meilisearch. Ensure the index is populated (e.g., via `meili-load`) before running CLI or agent queries.
- When introducing additional libraries later, check usage via Context7 per project guidance.
 - The `ask` command uses LangGraph with an LLM-driven controller that iteratively decides to search (keyword-only) or finish with a grounded answer. No vector embeddings are used.

LLM Setup
---------
- Set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, `OPENAI_BASE_URL`).
- Default model is `gpt-5-mini-2025-08-07`; override with `OPENAI_MODEL` if needed.
- The agent makes Chat Completions requests to produce JSON actions (search|final).
- Optional: `OPENAI_TEMPERATURE` (omit or set a number). If unset, provider default is used.
 - The HTTP server does not contact external models directly; it wraps the local agent which may use your configured LLM.

UV Workflow
-----------
- Create a venv and sync: `uv venv && uv sync`
- Install console script: `uv pip install -e .` then use `law ...`
- Ensure LangGraph is installed for agent: `uv sync` (installs `langgraph` from `pyproject.toml`)
4b) Load NDJSON cases (id, casetype, casename, facts) to Postgres:
```
uv run main.py pg-load-jsonl --jsonl /path/to/casename_classification/train.jsonl
# You can pass a directory to load all *.jsonl under it
```

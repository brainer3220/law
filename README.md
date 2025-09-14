Law CLI
=======

Command-line tool to explore the legal JSON dataset in `data/` and query a Postgres-backed full-text index (BM25 when available).

Usage
-----
- Preview a file: `uv run main.py preview "data/.../민사법_유권해석_요약_518.json"`
- Show stats: `uv run main.py stats`
- Agentic ask (LangGraph over Postgres): `uv run main.py ask "근로시간 면제업무 관련 판례 알려줘" --k 5 --max-iters 3`
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


HuggingFace LBOX Dataset
------------------------
Download the `lbox` casename classification dataset and convert it into per-document JSON files:

```
uv run scripts/import_hf_casename.py --split train
```

Use `--split` to select `train`, `valid`, `test`, or `test2`. Files are saved under `data/lbox_casename/<split>/`.
Set `HF_TOKEN` or `HUGGINGFACE_HUB_TOKEN` for private access.


Notes
-----
- Search prefers Postgres BM25. When unavailable, it falls back to DuckDB full-text search over the LBOX dataset (downloaded on demand) and finally to naive file scanning.
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

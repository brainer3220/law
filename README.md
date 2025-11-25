Law CLI
=======

Command-line tool to explore the legal JSON dataset in `data/` and query an OpenSearch-backed keyword index.

Monorepo Layout
--------------
```
repo-root/
├─ apps/
│  ├─ web/                # Next.js application
│  └─ api/                # FastAPI service managed by uv
├─ packages/
│  ├─ py-shared/          # Shared Python utilities (law_shared)
│  ├─ ts-schemas/         # Shared TypeScript schemas
│  ├─ ts-sdk/             # Generated SDK clients
│  └─ ui/                 # Reusable React UI primitives
├─ infra/                 # Dockerfiles and compose.yaml
├─ package.json           # Turborepo + pnpm scripts
├─ pnpm-workspace.yaml    # Workspace definition
├─ turbo.json             # Build graph configuration
└─ README.md
```

The API app relies on `uv` for dependency management; run `uv sync`
inside `apps/api/` to provision the virtual environment and install
both runtime and development extras. Shared Python code now lives in the
`law_shared` package under `packages/py-shared` and is consumed via a
`file://` dependency from the API service.

Usage
-----
- Preview a file: `uv run law-cli preview "data/.../민사법_유권해석_요약_518.json"`
- Show stats: `uv run law-cli stats`
- Search OpenSearch index: `uv run law-cli opensearch-search "가산금 면제" --limit 5`
- Agentic ask (LangGraph over OpenSearch): `uv run law-cli ask "근로시간 면제업무 관련 판례 알려줘" --k 5 --max-tool-calls 3`
- Serve OpenAI-compatible API: `uv run law-cli serve --host 127.0.0.1 --port 8080`
- Expose tools over MCP: `uv run law-mcp-server`

Use `--data-dir` or `LAW_DATA_DIR` to override the default `./data` corpus path when running dataset commands.

OpenAI-Compatible API (Streaming)
---------------------------------
Run the server:
```
uv run law-cli serve --host 127.0.0.1 --port 8080
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

Model Context Protocol (MCP)
---------------------------
Run the FastMCP server to expose the legal search tools over Streamable HTTP or StdIO transports:

```
uv run law-mcp-server  # defaults to streamable-http on :8000
```

- Override the dataset location with `LAW_DATA_DIR=/absolute/path/to/data`.
- Set `LAW_MCP_TRANSPORT=stdio` to integrate with Claude Desktop or other local hosts; the default `streamable-http` binds `/mcp` on port 8000.
- Inspect the contract locally with `uv run mcp dev packages/legal_tools/mcp_server.py`.

### Postgres-backed multi-turn chat

Set `LAW_CHAT_DB_URL` (defaults to `SUPABASE_DB_URL`, `DATABASE_URL`, or `PG_DSN` when unset) to enable the LangGraph `PostgresSaver` checkpoint store. The server will lazily
initialize a persistent chat graph, run `.setup()` on first use, and emit `X-Thread-ID` / `X-Checkpoint-ID` headers so callers can
resume conversations.

```
export LAW_CHAT_DB_URL="postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable"
export OPENAI_API_KEY=...

# first call creates a new thread (thread id returned in headers / body)
curl -i http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openai:gpt-4o-mini",
    "messages": [{"role":"user","content":"안녕! 넌 누구야?"}]
  }'

# reuse the thread for the follow-up turn
curl -i http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "thread_id": "thread-abc123",  # use the id from the previous response/header
    "messages": [{"role":"user","content":"내가 방금 뭐라고 했지?"}]
  }'

# inspect checkpoints (latest first)
curl -s http://127.0.0.1:8080/threads/thread-abc123/history | jq
```

Each turn is saved as a checkpoint keyed by `thread_id`, enabling replay, branching, or offline inspection via the HTTP history
endpoint.

Supabase/Postgres (optional; BM25 FTS)
-------------------------------------
Enable PostgreSQL-backed full-text search using ParadeDB BM25. This is optional; OpenSearch remains default.

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
uv run law-cli pg-init
```

4) Load local JSON to Postgres:
```
 uv run law-cli pg-load --data-dir data
```

5) Search with BM25:
```
uv run law-cli pg-search "근로시간 면제" --limit 5
```

Notes:
- Instance must have ParadeDB `pg_search` extension enabled. If not, request enablement or consider PGroonga/RUM (non-BM25) alternatives.

OpenSearch search & ingestion
-----------------------------
You can index the bundled sample documents into a running OpenSearch cluster (default URL: `http://localhost:9200`) and query them via CLI or Python.

1) Start OpenSearch locally (Docker example):
```
docker run -it --rm -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  opensearchproject/opensearch:2.15.0
```

2) Load the sample legal guidance files:
```
uv run law-cli opensearch-load --data-dir data/opensearch
```

3) Query from the CLI:
```
uv run law-cli opensearch-search "가산금 면제" --limit 5
```

4) Query from Python:
```python
from law_shared.legal_tools.opensearch_search import search_opensearch

for hit in search_opensearch("가산금 면제"):
    print(hit.title, hit.snippet)
```

Environment variables:
- `LAW_OPENSEARCH_URL` / `OPENSEARCH_URL` — override the base URL.
- `LAW_OPENSEARCH_API_KEY` — supply an API key; alternatively configure `LAW_OPENSEARCH_USERNAME` / `LAW_OPENSEARCH_PASSWORD` for basic auth.
- `LAW_OPENSEARCH_INDEX` — change the target index (defaults to `legal-docs`).

Sharing service
---------------
Run the FastAPI-powered sharing service that backs redactions, share links, and permission APIs:

```
uv run law-cli share-serve --host 127.0.0.1 --port 8081
```

- The service stores state in `LAW_SHARE_DB_URL` (defaults to `sqlite+pysqlite:///./share.db`). Provide a Postgres DSN to run it against a production database.
- Externally shared URLs are composed with `LAW_SHARE_BASE_URL` (defaults to `http://localhost:8081`). Set this to the public origin that clients use to open share links.
- Adjust link expiry defaults with `LAW_SHARE_LINK_TTL_DAYS` and increase token entropy via `LAW_SHARE_TOKEN_BYTES` if needed.
- To override the database without touching environment variables, pass `--db-url postgresql://...` on the CLI.

After the server starts, you can generate a share by first redacting a resource, creating the share, and then accessing it via the generated token:

```bash
# preview PII redactions
curl -s http://127.0.0.1:8081/v1/redactions/preview \
  -H 'Content-Type: application/json' \
  -d '{"payloads": {"body": "연락처 test@example.com API 키 sk-abc1234567890"}}'

# apply the redaction and persist the resource
curl -s http://127.0.0.1:8081/v1/redactions/apply \
  -H 'Content-Type: application/json' \
  -d '{
        "actor_id": "user-123",
        "resource": {"type": "conversation", "owner_id": "user-123"},
        "payloads": {"body": "연락처 test@example.com API 키 sk-abc1234567890"}
      }'

# create an unlisted share and generate an access link
curl -s http://127.0.0.1:8081/v1/shares \
  -H 'Content-Type: application/json' \
  -d '{
        "resource_id": "<RESOURCE_ID>",
        "actor_id": "user-123",
        "mode": "unlisted",
        "create_link": true,
        "link_domain_whitelist": ["share.test"]
      }'

# exchange the token for the shared payload (domain parameter optional if not whitelisted)
curl -s "http://127.0.0.1:8081/v1/s/<TOKEN>"
```

Replace `<RESOURCE_ID>` and `<TOKEN>` with values returned from the previous calls. Use `/v1/shares/{id}/revoke` to immediately invalidate a share and its tokens.

Background Worker (Whisper Transcription)
---------------------------------------
The API service includes a background worker for audio transcription using OpenAI Whisper.
This implementation uses FastAPI's `BackgroundTasks` and does not require Redis.

1) Start the API server:
```bash
cd apps/api
uv run uvicorn app.main:app --reload
```

2) Trigger transcription via API:
```bash
curl -X POST -F "file=@audio.mp3" -F "email=user@example.com" http://localhost:8000/transcribe/
```

Note: Job status and history are persisted in a SQLite database (`transcribe_jobs.db`). Set `TRANSCRIBE_DB_PATH` to customize the database location.




Notes
-----
- Search now uses OpenSearch. Ensure the index is populated (e.g., via `opensearch-load`) before running CLI or agent queries.
- When introducing additional libraries later, check usage via Context7 per project guidance.
 - The `ask` command uses LangGraph with an LLM-driven controller that iteratively decides to search (keyword-only) or finish with a grounded answer. No vector embeddings are used.

LLM Setup
---------
- Set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, `OPENAI_BASE_URL`).
- Default model is `gpt-5-mini-2025-08-07`; override with `OPENAI_MODEL` if needed.
- The agent makes Chat Completions requests to produce JSON actions (search|final).
- Optional: `OPENAI_TEMPERATURE` (omit or set a number). If unset, provider default is used.
 - The HTTP server does not contact external models directly; it wraps the local agent which may use your configured LLM.

LangSmith tracing
-----------------
The CLI and HTTP server can emit LangSmith traces for every `ask` call and chat completion. Provide the following environment
variables before running `uv run law-cli ...` or `law ...`:

- `LANGSMITH_API_KEY` — API key for your LangSmith workspace.
- `LANGSMITH_PROJECT` — Project name used to group runs.
- `LANGSMITH_ENDPOINT` — Optional; override the default `https://api.smith.langchain.com` endpoint.
- `LAW_LANGSMITH_ENABLED=0` — Optional toggle to disable tracing even when credentials exist.

When credentials are detected the app automatically sets `LANGCHAIN_TRACING_V2=true` and shares callback handlers with the
LangChain agent, multi-turn LangGraph, and HTTP server endpoints. The CLI, streaming API, and background Postgres chat manager
all report run metadata (top-k, iteration limits, thread IDs, checkpoint IDs) to the configured LangSmith project.

UV Workflow
-----------
- Create a venv and sync: `uv venv && uv sync`
- Install console script: `uv pip install -e .` then use `law ...`
- Ensure LangGraph is installed for agent: `uv sync` (installs `langgraph` from `pyproject.toml`)
4b) Load NDJSON cases (id, casetype, casename, facts) to Postgres:
```
uv run law-cli pg-load-jsonl --jsonl /path/to/casename_classification/train.jsonl
# You can pass a directory to load all *.jsonl under it
```

OpenSearch Stack
----------------
A Docker-based OpenSearch + Nori + k-NN environment for local experiments lives under `opensearch-nori-knn/`. See its [README](opensearch-nori-knn/README.md) for usage details.

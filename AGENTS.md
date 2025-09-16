# Repository Guidelines

## Project Structure & Module Organization
- `main.py` drives the CLI (`preview`, `stats`, `ask`, `serve`) and wires core services.
- Domain logic, LangChain adapters, and HTTP handlers live in `packages/legal_tools/`; statute and 해석례 tools reside in `packages/legal_tools/law_go_kr.py` and `agent_graph.py`.
- Shared schema contracts stay under `packages/legal_schemas/`; bump versions when fields change.
- Offline corpora, fixtures, and search indexes belong in `data/`; exclude large binaries from Git.
- Automation scripts live in `scripts/`; deterministic tests and fixtures live in `tests/`.

## Build, Test, and Development Commands
- `uv venv && uv sync` — create/update the Python ≥3.10 environment with LangChain/LangGraph deps.
- `uv run main.py ask "질문" --offline` — exercise the tool agent without network calls.
- `uv run main.py serve --host 127.0.0.1 --port 8080` — launch the OpenAI-compatible API server.
- `pytest -q` — run the offline pytest suite; add `-k pattern` or `-m slow` for targeting subsets.
- `ruff check .` / `ruff format .` — lint and format prior to commits.

## Coding Style & Naming Conventions
- Black-style formatting (~100 columns, 4-space indents); rely on `ruff format` for enforcement.
- Modules snake_case, classes PascalCase, constants UPPER_SNAKE_CASE, env vars SCREAMING_SNAKE_CASE.
- Annotate public functions, avoid wildcard imports, and keep comments focused on intent.

## Testing Guidelines
- Place tests in `tests/test_*.py`; use descriptive fixtures (e.g., `law_search_response_fixture`).
- Mock network/LLM calls; reuse JSON fixtures from `data/` to keep runs offline and deterministic.
- When altering retrieval flows, assert snippet ranking or citation payloads in regression tests.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`feat(agent): add law interpretation detail tool`).
- PRs should explain intent, outline main paths touched, link issues, and note `pytest`/`uv run` commands executed.
- Include before/after CLI or API samples when behavior or logging changes.

## Security & Configuration Tips
- Never commit secrets; mirror new variables in `.env.example` and document default fallbacks.
- Core env vars: `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, `OPENAI_*`, `GOOGLE_API_KEY`, `SUPABASE_DB_URL`, `PG_DSN`.
- Install `psycopg[binary]` (or system libpq) for Postgres BM25 search; ensure DSNs support SSL.

## Agent-Specific Instructions
- LangChain tool agent defaults to Postgres BM25; statute and 해석례 fallbacks live in `agent_graph.py`.
- Support OpenAI and Gemini: set `LAW_LLM_PROVIDER=gemini` when Gemini keys exist; keep prompts provider-neutral.
- Use the Context7 MCP for third-party API docs and the ast-grep MCP for repo-wide pattern searches before refactors.

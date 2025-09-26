# Repository Guidelines

## Project Structure & Module Organization
- `main.py` drives the CLI commands (`preview`, `stats`, `ask`, `serve`) and wires core services.
- Domain logic, LangChain adapters, and HTTP handlers live under `packages/legal_tools/`; statute and 해석례 tooling is in `packages/legal_tools/law_go_kr.py` and `packages/legal_tools/agent_graph.py`.
- Shared schemas stay in `packages/legal_schemas/`; bump the version field whenever payloads change.
- Offline corpora, fixtures, and search indexes belong in `data/`; omit large binaries from Git.
- Automation scripts sit in `scripts/`, while deterministic tests and fixtures land in `tests/`.

## Build, Test, and Development Commands
- `uv venv && uv sync` — provision the Python ≥3.10 environment with LangChain/LangGraph deps.
- `uv run main.py ask "질문" --offline` — exercise the agent without network calls.
- `uv run main.py serve --host 127.0.0.1 --port 8080` — expose the OpenAI-compatible HTTP API.
- `pytest -q` — run the offline test suite; add `-k name` to target subsets.
- `ruff check .` / `ruff format .` — lint and auto-format before committing.

## Coding Style & Naming Conventions
Adopt Black-style formatting (≈100 cols, 4-space indents) enforced by `ruff format`. Modules use snake_case, classes PascalCase, constants UPPER_SNAKE_CASE, and environment variables SCREAMING_SNAKE_CASE. Annotate public functions, avoid wildcard imports, and keep comments focused on intent.

## Testing Guidelines
Write pytest cases under `tests/test_*.py`, mirroring new fixtures in `data/` when needed. Mock external LLM and network calls so runs stay offline and deterministic. When adjusting retrieval flows, assert snippet ranking or citation payloads to prevent regressions.

## Commit & Pull Request Guidelines
Follow Conventional Commits (e.g., `feat(agent): add statute parser fallback`). PRs should outline intent, main touch points, linked issues, and note `pytest`/`uv run` commands executed. Include before/after CLI or API samples when behavior or logging changes.

## Security & Configuration Tips
Never commit secrets; document defaults in `.env.example`. Core env vars include `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, `OPENAI_*`, `GOOGLE_API_KEY`, `SUPABASE_DB_URL`, and `PG_DSN`. Install `psycopg[binary]` or system `libpq` for Postgres BM25 search, and ensure DSNs enforce SSL.

## Agent-Specific Instructions
The LangChain agent defaults to Postgres BM25; statute and 해석례 fallbacks reside in `packages/legal_tools/agent_graph.py`. Prompts must stay provider-neutral to support OpenAI and Gemini; set `LAW_LLM_PROVIDER=gemini` when Gemini keys are configured. Keep retrieval indexes under `data/` and regenerate them via project scripts rather than manual edits.

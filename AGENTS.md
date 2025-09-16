# Repository Guidelines

## Project Structure & Module Organization
- `main.py` is the CLI entry point (`preview`, `stats`, `ask`, `serve`, Postgres helpers).
- Core agent logic, tool adapters, and the HTTP server live in `packages/legal_tools/`.
- Shared data contracts belong in `packages/legal_schemas/`; keep new schemas versioned.
- Offline corpora and fixtures sit under `data/`; large artifacts stay out of Git.
- Automation scripts live in `scripts/`; end-to-end tests and fixtures live in `tests/`.

## Build, Test, and Development Commands
- `uv venv && uv sync` creates a Python ≥3.10 environment with LangChain/LangGraph deps.
- `uv run main.py ask "질문" --offline` exercises the LangChain tool agent without network calls.
- `uv run main.py serve --host 127.0.0.1 --port 8080` runs the OpenAI-compatible API server.
- `pytest -q` runs the full offline test suite; add `-k pattern` or `-m slow` as needed.
- `ruff check .` and `ruff format .` keep style consistent before each commit.

## Coding Style & Naming Conventions
- Use Black-compatible formatting (~100 columns, 4-space indents) and follow Ruff defaults.
- Modules stay snake_case, classes PascalCase, constants UPPER_SNAKE_CASE, env vars SCREAMING_SNAKE_CASE.
- Type-hint public interfaces; prefer explicit imports over wildcards; keep comments concise and functional.

## Testing Guidelines
- Write pytest tests under `tests/test_*.py`; name fixtures descriptively (`*_fixture`).
- Keep tests deterministic and offline—mock LLM calls and rely on samples in `data/`.
- When touching retrieval, add regression tests that assert evidence ranking or citation shape.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat(ask): add Gemini support`).
- PRs should state intent, summarize major code paths, list `pytest`/`uv run` commands, and link issues.
- Include before/after CLI or API snippets when behavior changes or logs are relevant.

## Security & Configuration Tips
- Never commit secrets; mirror new variables in `.env.example`.
- Key env vars: `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, `OPENAI_*`, `GOOGLE_API_KEY`, `SUPABASE_DB_URL`/`PG_DSN`.
- Install `psycopg[binary]` for Postgres search and configure SSL-friendly DSNs.

## Agent-Specific Instructions
- The LangChain tool agent prefers Postgres BM25; fall back handling lives in `packages/legal_tools/agent_graph.py`.
- Support both OpenAI and Gemini: set `LAW_LLM_PROVIDER=gemini` (or rely on detected keys) and keep prompts provider-neutral.
- Use the Context7 MCP for third-party API docs and ast-grep MCP for repository-wide pattern searches before refactors.

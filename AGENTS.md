# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: CLI entry. Commands: `preview`, `stats`, `ask`, `serve`, optional Postgres: `pg-init`, `pg-load`, `pg-search`.
- `packages/legal_tools/`: Agent + search utilities.
  - `agent_graph.py`: LangGraph multi‑round Q&A (keyword retrieval only).
  - `api_server.py`: OpenAI‑compatible, streaming Chat Completions API.
  - `pg_search.py`: Postgres BM25/FTS wrapper (optional backend).
- `packages/legal_schemas/`: Pydantic models.
- `data/`: Local JSON corpus (large files stay here).
- `scripts/`: Maintenance/import helpers. `tests/`: Pytest suite (add as needed).

## Build, Test, and Development Commands
- Setup: `uv venv && uv sync` (Python ≥3.10).
- Ask (CLI): `uv run main.py ask "근로시간 면제" --k 5 --max-iters 3`.
- Serve API: `uv run main.py serve --host 127.0.0.1 --port 8080`.
- Postgres (optional): `uv run main.py pg-init`; `pg-load --data-dir data`; `pg-search "질의" --limit 5`.
- Tests: `pytest -q` (optionally `-k pattern`). Keep tests offline/deterministic.

## Coding Style & Naming Conventions
- Python typing for public APIs. Modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Prefer Black/isort/Ruff if configured; otherwise keep Black‑compatible formatting (line length ~100).
- Keep changes minimal and focused; avoid drive‑by refactors.

## Testing Guidelines
- Use pytest; place tests under `tests/` named `test_*.py` (e.g., `tests/test_ask.py`).
- Target behaviors: Postgres search wrappers, agent loop (decide → search → finalize), CLI formatting.
- Run fast, hermetic tests; no network/API keys required.

## Commit & Pull Request Guidelines
- Conventional Commits (e.g., `feat(ask): emit structured Markdown`, `chore(api): set default model`).
- PRs include: purpose, concise change summary, test plan (commands + expected output), and linked issues.
- If CLI/API output changes, include before/after samples or curl traces.

## Security & Configuration Tips
- Do not commit secrets/PII. Use `.env.example`.
- Env vars: `LAW_DATA_DIR` (data root), `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-5-mini-2025-08-07`), `OPENAI_BASE_URL`. For Postgres: `SUPABASE_DB_URL` or `PG_DSN`.
- Keep heavy artifacts under `data/` and out of VCS.

## Agent‑Specific Instructions
- When using an external library, use Context7 MCP to find API docs and examples.
- Use the ast‑grep MCP for code search across the repo.

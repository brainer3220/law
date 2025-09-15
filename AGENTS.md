# Repository Guidelines

## Project Structure & Module Organization
- `main.py` — CLI entry; commands: `preview`, `stats`, `ask`, `serve`, `pg-init`, `pg-load`, `pg-load-jsonl`, `pg-search`.
- `packages/legal_tools/` — Agent graph, Postgres search, API (`agent_graph.py`, `pg_search.py`, `api_server.py`).
- `packages/legal_schemas/` — Pydantic models for I/O schemas.
- `data/` — Local corpora (JSON/JSONL). Large artifacts belong here, not in Git.
- `scripts/` — Import/maintenance helpers.
- `tests/` — Pytest suite.

## Build, Test, and Development Commands
- Setup (Python ≥3.10): `uv venv && uv sync`
- Run agent: `uv run main.py ask "근로시간 면제" --k 5 --max-iters 3`
- Serve API: `uv run main.py serve --host 127.0.0.1 --port 8080`
- Postgres: `uv run main.py pg-init`; load dir: `uv run main.py pg-load --data-dir data`; load JSONL: `uv run main.py pg-load-jsonl --file data/foo.jsonl`; search: `uv run main.py pg-search "질의" --limit 5`
- Tests: `pytest -q` (filter via `-k pattern`). Keep tests offline/deterministic.

## Coding Style & Naming Conventions
- Type hints for all public APIs.
- Naming: modules `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE_CASE`.
- Formatting: Black-compatible (~100 cols). Prefer `black`, `isort`, and `ruff` if configured.
- Keep changes minimal and scoped; avoid drive‑by refactors.

## Testing Guidelines
- Framework: Pytest; tests under `tests/` named `test_*.py`.
- Focus: Postgres search wrappers, agent loop (decide → search → finalize), CLI output formatting.
- Tests must run without network or API keys. Use small, local fixtures under `data/`.

## Commit & Pull Request Guidelines
- Conventional Commits (e.g., `feat(ask): add --flex and context`).
- PRs include purpose, concise change summary, test plan (commands + expected output), and linked issues. If CLI/API output changes, include before/after samples or curl traces.

## Security & Configuration Tips
- Never commit secrets/PII. Use `.env.example`.
- Key env vars: `LAW_DATA_DIR`, `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-5-mini-2025-08-07`), `OPENAI_BASE_URL`, `SUPABASE_DB_URL` or `PG_DSN`.
- Keep heavy artifacts under `data/` and out of VCS.

## Agent‑Specific Instructions
- When using an external library, use Context7 MCP to find API docs and examples.
- Use the ast‑grep MCP for code search across the repo.
- Keep tests offline and deterministic.

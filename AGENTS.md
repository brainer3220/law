# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: CLI entry. Commands: `preview`, `stats`, `ask`, `serve`, Postgres: `pg-init`, `pg-load`, `pg-load-jsonl`, `pg-search`.
- `packages/legal_tools/`: Agent + search utilities (`agent_graph.py`, `pg_search.py`, `api_server.py`).
- `packages/legal_schemas/`: Pydantic models.
- `data/`: Local JSON/JSONL corpora (large files live here).
- `scripts/`: Import/maintenance helpers. `tests/`: Pytest suite.

## Build, Test, and Development Commands
- Setup: `uv venv && uv sync` (Python ≥3.10).
- Run agent: `uv run main.py ask "근로시간 면제" --k 5 --max-iters 3`.
- Serve API: `uv run main.py serve --host 127.0.0.1 --port 8080`.
- Postgres (optional): `uv run main.py pg-init`; `uv run main.py pg-load --data-dir data`; `uv run main.py pg-search "질의" --limit 5`.
- Tests: `pytest -q` (use `-k pattern` to filter). Keep tests offline/deterministic.

## Coding Style & Naming Conventions
- Use type hints for public APIs. Modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Follow Black-compatible formatting (~100 cols); prefer Black/isort/Ruff if configured.
- Keep changes minimal and scoped; avoid drive‑by refactors.

## Testing Guidelines
- Framework: Pytest. Place tests under `tests/` named `test_*.py` (e.g., `tests/test_ask.py`).
- Focus: Postgres search wrappers, agent loop (decide → search → finalize), CLI output formatting.
- Tests must be fast, hermetic, and not require network/API keys.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat(ask): add --flex and context`).
- PRs include purpose, concise change summary, test plan (commands + expected output), and linked issues.
- If CLI/API output changes, include before/after samples or curl traces.

## Security & Configuration Tips
- Never commit secrets/PII. Use `.env.example`.
- Key env vars: `LAW_DATA_DIR` (data root), `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-5-mini-2025-08-07`), `OPENAI_BASE_URL`, `SUPABASE_DB_URL` or `PG_DSN`.
- Keep heavy artifacts under `data/` and out of VCS.

## Agent‑Specific Instructions
- When using an external library, use Context7 MCP to find API docs and examples.
- Use the ast‑grep MCP for code search across the repo.

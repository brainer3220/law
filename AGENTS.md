# Repository Guidelines

## Project Structure & Module Organization
- `main.py` drives the CLI (`preview`, `stats`, `ask`, `serve`, Postgres helpers).
- Core agents and services live in `packages/legal_tools/` (agent graph, search, API server).
- Shared schemas sit in `packages/legal_schemas/` for typed I/O contracts.
- Importable corpora belong under `data/`; keep large artifacts out of Git.
- Maintenance scripts live in `scripts/`; automated checks reside in `tests/` with pytest.

## Build, Test, and Development Commands
- `uv venv && uv sync` provisions a Python ≥3.10 environment with project deps.
- `uv run main.py ask "질문" --offline` exercises the agent end-to-end without network use.
- `uv run main.py serve --host 127.0.0.1 --port 8080` launches the local API server.
- `pytest -q` runs the full offline test suite; add `-k pattern` to scope failures quickly.

## Coding Style & Naming Conventions
- Follow Black-compatible formatting (~100 columns) and keep modules snake_case, classes PascalCase, constants UPPER_SNAKE_CASE.
- Type-hint all public interfaces and prefer explicit imports over wildcards.
- Before committing, run `ruff check .` and `ruff format .` if tooling is configured locally.

## Testing Guidelines
- Tests use pytest; files live under `tests/` named `test_*.py`.
- Keep fixtures deterministic and local—never hit remote APIs; rely on samples in `data/`.
- Introduce targeted tests when touching agent loops, Postgres search wrappers, or CLI formatting.

## Commit & Pull Request Guidelines
- Use Conventional Commits, e.g., `feat(ask): add offline retries`.
- Pull requests should describe purpose, summarize changes, list test commands with expected results, and link related issues or tickets.
- Include before/after CLI or API output when behavior changes.

## Security & Configuration Tips
- Never commit secrets; mirror new env vars in `.env.example`.
- Respect `LAW_OFFLINE=1`, `OPENAI_*`, and `SUPABASE_DB_URL`/`PG_DSN` settings; default model is `gpt-5-mini-2025-08-07`.
- Store bulky corpora or generated artifacts under `data/` to keep the repo lightweight.

## Agent-Specific Instructions
- When referencing third-party APIs, pull examples via the Context7 MCP.
- Use ast-grep MCP for code search across the repository before modifying existing logic.

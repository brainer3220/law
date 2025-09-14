# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: CLI entry with commands `search`, `preview`, `stats`, `reindex`, `ask`.
- `packages/legal_tools/`: Search + agent runtime.
  - `agent_graph.py`: LangGraph multi‑round Q&A (keyword retrieval).
  - `contextual_rag.py`: Optional chunking utilities (not required by CLI).
- `packages/legal_schemas/`: Pydantic models (e.g., `Document`, `Section`).
- `data/`: JSON corpus and DuckDB index (`data/records.duckdb`).
- `scripts/`: Maintenance tasks.  `tests/`: Pytest suite.

## Build, Test, and Development Commands
- Environment: `uv venv && uv sync` (Python 3.11+).
- Search: `uv run main.py search "주40시간제" --limit 5`.
- Agent Q&A: `uv run main.py ask "근로시간 면제업무 판례 알려줘" --k 5 --max-iters 3`.
- Reindex cache: `uv run main.py reindex` (rebuilds DuckDB + FTS index).
- Tests: `pytest -q` (filter with `-k pattern`).
- Lint/format: `pre-commit run -a` (Black, isort, Ruff).

## Coding Style & Naming Conventions
- Python 3.11+. Use type hints for public APIs.
- Formatting: Black (line length 100), isort (profile=black), Ruff linting.
- Naming: modules `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep changes minimal and focused; avoid drive‑by refactors.

## Testing Guidelines
- Framework: pytest. Keep tests offline/deterministic; do not require network/API keys.
- Priorities: DuckDB indexing/search (incl. FTS), agent routing (plan → retrieve → assess → synthesize).
- Place tests under `tests/` and name by feature (e.g., `test_search.py`).
- Run: `pytest -q` and optionally `-k <pattern>`.

## Commit & Pull Request Guidelines
- Commits: Conventional Commits (e.g., `feat: add ask agent`, `fix: duckdb reindex`).
- PRs: include purpose, concise change summary, test plan (commands + expected output), and linked issues.
- When UX/CLI output changes, attach before/after samples.

## Security & Configuration Tips
- Offline‑first; never commit secrets or PII. Use `.env.example` for local settings.
- Use `LAW_DATA_DIR` to point the CLI at a custom data folder; default is `./data`.
- Keep heavy artifacts in `data/`; do not commit large files.

## Agent‑Specific Instructions
- When using an external library, use Context7 MCP to find API docs and examples.
- Use the ast‑grep MCP for code search across the repo.

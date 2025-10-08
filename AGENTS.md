# Repository Guidelines

## Project Structure & Module Organization
- `main.py` drives the CLI entry points (`preview`, `stats`, `ask`, `serve`) and wires shared services.
- Domain logic and adapters live under `packages/legal_tools/`; statute and 해석례 flows concentrate in `law_go_kr.py` and `agent_graph.py`.
- Shared payload schemas reside in `packages/legal_schemas/`; bump their version whenever request/response shapes change.
- Offline corpora, fixtures, and retrieval indexes belong in `data/`, while tests sit in `tests/` and utility scripts in `scripts/`.

## Build, Test, and Development Commands
- `uv venv && uv sync` provisions the Python ≥3.10 environment with all LangChain/LangGraph dependencies.
- `uv run main.py ask "질문" --offline` exercises the agent locally without remote API calls.
- `uv run main.py serve --host 127.0.0.1 --port 8080` launches the OpenAI-compatible HTTP endpoint for manual QA.
- `pytest -q` runs the offline unit and integration suite; add `-k pattern` to scope execution.
- `ruff check .` and `ruff format .` keep code style consistent—run them before submitting changes.

## Coding Style & Naming Conventions
- Follow Black-style formatting (≈100 columns, 4-space indentation) enforced through `ruff format`.
- Prefer snake_case for modules and functions, PascalCase for classes, and UPPER_SNAKE_CASE for constants and environment variables.
- Annotate public functions, avoid wildcard imports, and keep comments focused on intent rather than mechanics.

## Testing Guidelines
- Write pytest cases under `tests/test_*.py`; mirror new fixtures in `data/` so offline runs stay deterministic.
- Mock LLM or network integrations to keep tests reliable; assert retrieval ranks or citation payloads when modifying agent flows.
- Aim for comprehensive coverage on schema changes and critical retrieval logic before opening a pull request.

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat(agent): add statute parser fallback`) and group related changes logically.
- PR descriptions should state intent, major touch points, linked issues, and list the `uv run` and `pytest` commands exercised.
- Include CLI or API before/after samples when behavior or logging changes, and highlight schema version bumps.

## Security & Configuration Tips
- Never commit secrets; document defaults in `.env.example` and rely on environment variables like `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, and `OPENAI_*`.
- Install `psycopg[binary]` or system `libpq` for Postgres-backed BM25 search, enforcing SSL in DSNs.
- Keep retrieval indexes under `data/` and regenerate them via project scripts rather than manual edits to ensure reproducibility.

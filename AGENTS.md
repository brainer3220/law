# Repository Guidelines

This guide helps new contributors navigate the legal agent stack and deliver consistent changes.

## Project Structure & Module Organization
- `main.py` exposes CLI entry points (`preview`, `stats`, `ask`, `serve`) and wires shared services.
- Core agent flows live under `packages/legal_tools/`; statute retrieval centers on `law_go_kr.py`, orchestration on `agent_graph.py`.
- Shared Pydantic schemas reside in `packages/legal_schemas/`; bump their versions whenever payloads change.
- Offline corpora, retrieval artifacts, and fixtures belong in `data/`; tests live in `tests/`; helper scripts sit in `scripts/`.

## Build, Test, and Development Commands
- `uv venv && uv sync` sets up Python ≥3.10 with LangChain/LangGraph dependencies.
- `uv run main.py ask "질문" --offline` runs the agent on local corpora; append `--trace` for verbose debugging.
- `uv run main.py serve --host 127.0.0.1 --port 8080` serves the OpenAI-compatible HTTP interface for manual QA.
- `pytest -q` executes unit and integration suites; pass `-k pattern` to scope scenarios.
- `ruff check .` and `ruff format .` ensure lint and formatting compliance; run both before committing.

## Coding Style & Naming Conventions
- Follow Black conventions (4-space indentation, ~100 columns) via `ruff format`.
- Use snake_case for modules and functions, PascalCase for classes, and UPPER_SNAKE_CASE for constants and env vars.
- Type-annotate public APIs, avoid wildcard imports, and reserve comments for intent or edge cases.

## Testing Guidelines
- Add pytest modules as `tests/test_*.py`; mirror new fixtures in `data/` to keep offline runs deterministic.
- Mock network/LLM calls and assert retrieval ranks or statute citations when altering agent flows.
- Prefer regression tests covering schema version changes, prompt templates, or ranking heuristics.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat(agent): …`, `fix(schema): …`) and group related edits logically.
- PRs should capture intent, major touch points, linked issues, and commands executed (`uv run`, `pytest`).
- Include CLI/API before/after snippets for behavior changes and call out schema bumps explicitly.

## Security & Configuration Tips
- Never commit secrets; document defaults in `.env` or `.env.example` and rely on `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, `OPENAI_*`.
- Install `psycopg[binary]` or system `libpq` for Postgres-backed BM25 search and enforce SSL in DSNs.
- Regenerate retrieval indexes via project scripts rather than manual edits to keep deployments reproducible.

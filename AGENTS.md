# Repository Guidelines

## Project Structure & Module Organization
- `main.py` orchestrates CLI commands (`preview`, `stats`, `ask`, `serve`) and wires core services.
- Domain logic, LangChain adapters, and HTTP handlers live in `packages/legal_tools/`; statute and 해석례 flows center on `packages/legal_tools/law_go_kr.py` and `packages/legal_tools/agent_graph.py`.
- Shared schemas stay in `packages/legal_schemas/`; increment the version field whenever payloads change.
- Offline corpora, fixtures, and indexes belong under `data/`; keep large binaries out of Git.
- Tests reside in `tests/`, scripts in `scripts/`, and automation/config assets are grouped accordingly.

## Build, Test, and Development Commands
- `uv venv && uv sync` — provision the Python ≥3.10 environment with LangChain/LangGraph dependencies.
- `uv run main.py ask "질문" --offline` — exercise the agent locally without invoking remote APIs.
- `uv run main.py serve --host 127.0.0.1 --port 8080` — launch the OpenAI-compatible HTTP endpoint.
- `pytest -q` — run the offline unit and integration suite; add `-k pattern` for targeted runs.
- `ruff check .` / `ruff format .` — lint and format codebase-wide.

## Coding Style & Naming Conventions
- Adopt Black-style formatting (≈100 columns, 4-space indentation) enforced by `ruff format`.
- Use snake_case modules, PascalCase classes, UPPER_SNAKE_CASE constants, and SCREAMING_SNAKE_CASE environment variables.
- Annotate public functions, avoid wildcard imports, and keep comments focused on intent.

## Testing Guidelines
- Author pytest cases under `tests/test_*.py`; mirror fixtures in `data/` when expanding coverage.
- Mock external LLM and network calls so test runs remain deterministic.
- When updating retrieval flows, assert snippet ranking or citation payloads to prevent regressions.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (e.g., `feat(agent): add statute parser fallback`).
- PRs should summarize intent, main touch points, linked issues, and note `pytest`/`uv run` commands executed.
- Include before/after CLI or API samples when behavior or logging changes; highlight schema bumps in `packages/legal_schemas/`.

## Security & Configuration Tips
- Never commit secrets; document defaults in `.env.example` and rely on environment variables like `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, and `OPENAI_*`.
- Install `psycopg[binary]` or system `libpq` for Postgres BM25 search, ensuring DSNs enforce SSL.
- Keep retrieval indexes under `data/`; regenerate via project scripts rather than manual edits.

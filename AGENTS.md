# Repository Guidelines

This guide orients contributors so every change to the legal agent stack remains deterministic, reviewable, and ship-ready.

## Project Structure & Module Organization
- `main.py` anchors CLI entry points (`preview`, `stats`, `ask`, `serve`) and wires shared services.
- Core agent behaviors live under `packages/legal_tools/`; start with `law_go_kr.py` for retrieval and `agent_graph.py` for orchestration flows.
- Shared payload definitions live in `packages/legal_schemas/`; bump versions when request/response shapes evolve.
- Deterministic corpora and fixtures sit in `data/`; integration specs in `tests/`; operational scripts in `scripts/`.

## Build, Test, and Development Commands
- `uv venv && uv sync` provisions Python ≥3.10 and installs pinned LangChain/LangGraph dependencies.
- `uv run main.py ask "질문" --offline` exercises the retrieval agent; add `--trace` for streaming debug spans.
- `uv run main.py serve --host 127.0.0.1 --port 8080` launches the OpenAI-compatible HTTP façade for QA.
- `pytest -q` runs unit and integration suites; add `-k pattern` to isolate flaky cases.
- `ruff check .` and `ruff format .` keep lint and formatting aligned with Black conventions.

## Coding Style & Naming Conventions
- Stick to 4-space indentation, ~100-column lines, and deterministic imports enforced by Ruff.
- Prefer snake_case for modules/functions, PascalCase for classes, and UPPER_SNAKE_CASE for constants or env vars.
- Type-annotate public APIs, avoid wildcard imports, and add comments only for intent or edge constraints.

## Testing Guidelines
- Add scenarios as `tests/test_*.py`; mirror any new fixtures under `data/` to keep offline runs reproducible.
- Mock network or LLM calls and assert retrieval ranks, statute citations, or schema versions when flows change.
- Gate merges on a green `pytest -q`; consider adding regression cases when prompts or ranking heuristics shift.

## Commit & Pull Request Guidelines
- Use Conventional Commits (`feat(agent):`, `fix(schema):`, etc.) and group changes by feature.
- PRs should reference issues, list touched packages/modules, note commands executed, and include CLI/API before-after snippets for behavioral shifts.

## Security & Configuration Tips
- Never commit secrets; rely on `.env.example` and `LAW_OFFLINE`, `LAW_LLM_PROVIDER`, `OPENAI_*` defaults.
- Install `psycopg[binary]` or system `libpq` for Postgres-backed BM25 search and enforce SSL in DSNs.
- Regenerate retrieval indexes via project scripts rather than manual edits to maintain reproducibility.

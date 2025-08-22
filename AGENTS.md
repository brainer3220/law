# Repository Guidelines

## Project Structure & Module Organization
- Source: core modules at repo root — `main.py` (FastAPI app), `config.py`, `models.py`, `data_loader.py`, `retrievers.py`, `cache_manager.py`, `model_manager.py`.
- CLI/Toolkit: `manage.py` (UV-powered dev tasks), `run_api.py` (alt runner), `scripts/` (helpers).
- Tests: `tests/` with unit, integration, e2e, performance, stress suites; shared fixtures in `tests/conftest.py`.
- Assets & runtime: `datasets/`, `cache/`, `logs/` (created by setup); env in `.env` (see `.env.example`).
- Packaging & infra: `pyproject.toml` (hatch + deps), `Dockerfile`, `docker-compose.yml`.

## Build, Test, and Development Commands
- Setup: `python manage.py setup` — create dirs and `.env`.
- Install: `python manage.py install [--dev] [--gpu]` — sync deps via UV.
- Run API: `python manage.py start [--host 0.0.0.0] [--port 8000] [--no-reload]`.
- Tests (quick): `python manage.py test [unit|integration|performance|e2e|all] [--coverage]`.
- Tests (full control): `uv run python -m pytest tests/ -v --cov=. --cov-report=html`.
- Lint/Format: `python manage.py lint` and `python manage.py format`.
- Docker (optional): `docker compose up --build`.

## Coding Style & Naming Conventions
- Formatter: Black (line length 100); Imports: isort (profile=black).
- Linters/Types: flake8, mypy (prefer type hints on public functions).
- Indentation & names: 4 spaces; modules/functions `snake_case`; classes `CamelCase`; tests `test_*.py`, classes `Test*`, functions `test_*`.
- Keep endpoints, models, and config cohesive; avoid side effects at import time.

## Testing Guidelines
- Framework: pytest with markers (`unit`, `integration`, `performance`, `e2e`, `stress`, etc.).
- Coverage: target ≥80% (see `pyproject.toml`); HTML at `htmlcov/index.html`, XML at `test_reports/coverage.xml`.
- Conventions: fast unit tests by default; mark slow/network tests appropriately. Use fixtures in `conftest.py`.

## Commit & Pull Request Guidelines
- Messages: imperative mood; concise subject; optional type prefix (`feat:`, `fix:`, `refactor:`); include scope when helpful.
- PRs must: describe changes and motivation, link issues, include test plan/output, update docs as needed, and pass lint/format/tests.
- Before pushing: `python manage.py format && python manage.py lint && uv run python -m pytest -v`.

## Security & Configuration Tips
- Do not commit secrets. Use `.env`; start from `.env.example`.
- Large data, caches, and logs are ignored; keep them out of commits.
- Prefer UV for running tools (`uv run ...`) to ensure the project venv and locked deps are used.


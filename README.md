Law MVP CLI
=================

Simple command-line tool to explore the legal JSON dataset in `data/`.

Usage
-----
- Search by keyword: `uv run main.py search "주40시간제" --limit 5`
- Preview a file: `uv run main.py preview "data/.../민사법_유권해석_요약_518.json"`
- Show stats: `uv run main.py stats`

Notes
-----
- No external dependencies are required.
- All operations are file-based and offline.
- When introducing libraries later, check usage via Context7 per project guidance.

UV Workflow
-----------
- Create a venv and sync: `uv venv && uv sync`
- Run without installing: `uv run main.py search "주40시간제" --limit 5`
- Install console script: `uv pip install -e .` then use `law search "주40시간제"`
- Alternative run: `uv run law stats` (after editable install)

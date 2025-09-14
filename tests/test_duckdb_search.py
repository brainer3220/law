import importlib.util
import json
from pathlib import Path
import sys as _sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "duckdb_search", ROOT / "packages" / "legal_tools" / "duckdb_search.py"
)
duckdb_search = importlib.util.module_from_spec(spec)
assert spec and spec.loader
_sys.modules[spec.name] = duckdb_search  # type: ignore[assignment]
spec.loader.exec_module(duckdb_search)  # type: ignore[attr-defined]
search_fts = duckdb_search.search_fts


def test_duckdb_search(tmp_path: Path) -> None:
    data = tmp_path / "cases.jsonl"
    records = [
        {"id": "1", "casetype": "civil", "casename": "근로시간 사건", "facts": "주 40시간제 관련 판결"},
        {"id": "2", "casetype": "criminal", "casename": "절도 사건", "facts": "절도 혐의"},
    ]
    with data.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    res = search_fts("근로시간", limit=5, hf_path=str(data), db_path=tmp_path / "cases.duckdb")
    assert res and res[0]["doc_id"] == "1"

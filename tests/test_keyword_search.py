import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "keyword_search", ROOT / "packages" / "legal_tools" / "keyword_search.py"
)
keyword_search = importlib.util.module_from_spec(spec)
assert spec and spec.loader
import sys as _sys
_sys.modules[spec.name] = keyword_search  # type: ignore[assignment]
spec.loader.exec_module(keyword_search)  # type: ignore[attr-defined]
search_files = keyword_search.search_files


def _write_doc(d: Path, doc_id: str, title: str, sentences: list[str]) -> None:
    obj = {"info": {"doc_id": doc_id, "title": title}, "taskinfo": {"sentences": sentences}}
    (d / f"{doc_id}.json").write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")


def test_keyword_search(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_doc(data_dir, "1", "근로시간 단축", ["주 40시간제" ])
    _write_doc(data_dir, "2", "형사 사건", ["절도 혐의"])
    hits = search_files("근로시간", limit=5, data_dir=data_dir)
    assert hits and hits[0].doc_id == "1"

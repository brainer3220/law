from __future__ import annotations

import json
from pathlib import Path

from scripts.meilisearch_load import collect_documents, chunked


def make_sample(path: Path) -> None:
    sample = {
        "info": {
            "doc_id": "DOC-1",
            "title": "근로기준법 질의 회신",
            "response_institute": "고용노동부",
            "response_date": "2024-01-05",
            "taskType": "행정해석",
        },
        "taskinfo": {
            "instruction": "근로시간 특례 조항 설명",
            "sentences": ["근로기준법 제59조 특례"],
            "output": "특례 적용 업종과 절차를 안내했습니다.",
        },
    }
    path.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")


def test_collect_documents_builds_expected_fields(tmp_path: Path) -> None:
    data_dir = tmp_path / "docs"
    data_dir.mkdir()
    make_sample(data_dir / "sample.json")

    docs = collect_documents(data_dir)
    assert len(docs) == 1
    doc = docs[0]
    assert doc["id"] == "DOC-1"
    assert doc["title"].startswith("근로기준법")
    assert "특례 적용" in doc["body"]
    assert doc["meta"]["info"]["doc_id"] == "DOC-1"
    assert doc["response_institute"] == "고용노동부"


def test_collect_documents_skips_invalid_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "docs"
    data_dir.mkdir()
    make_sample(data_dir / "sample.json")
    (data_dir / "invalid.json").write_text("{not valid json", encoding="utf-8")

    docs = collect_documents(data_dir)
    assert len(docs) == 1
    assert docs[0]["id"] == "DOC-1"


def test_chunked_batches_list(tmp_path: Path) -> None:
    batches = list(chunked([{"id": str(i)} for i in range(5)], 2))
    assert len(batches) == 3
    assert [len(b) for b in batches] == [2, 2, 1]


def test_chunked_handles_empty_list() -> None:
    assert list(chunked([], 3)) == []

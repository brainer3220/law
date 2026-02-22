from __future__ import annotations

from pathlib import Path

import pytest

from law_shared.legal_tools.agent_graph import tool_keyword_search
from law_shared.legal_tools.file_index_sqlite import rebuild_index
from law_shared.legal_tools.file_normalize import normalize_documents
from law_shared.legal_tools.file_search import FileSearchHit, search_local_index
from law_shared.legal_tools.file_store import (
    load_sync_state,
    raw_root,
    save_snapshot,
    utc_now,
)
from law_shared.legal_tools.file_sync import sync_source
from law_shared.legal_tools.law_go_kr import (
    LawDetailResponse,
    LawSearchResponse,
    LawSearchResult,
)


def test_normalize_index_search_roundtrip(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    collected_at = utc_now()
    payload = {
        "source_type": "statute",
        "source_id": "009682",
        "version": "2020-01-01-17000",
        "collected_at": "2026-02-22T00:00:00Z",
        "search_result": {"title": "자동차관리법"},
        "detail": {
            "title": "자동차관리법",
            "doc_type": "법률",
            "ministry": "국토교통부",
            "promulgation_date": "2020-01-01",
            "enforcement_date": "2020-07-01",
            "promulgation_number": "17000",
            "articles": [
                {
                    "article_no": "제1조",
                    "title": "목적",
                    "content": "이 법은 자동차를 효율적으로 관리하기 위함이다.",
                    "paragraphs": [],
                }
            ],
        },
    }
    save_snapshot(
        data_dir=data_dir,
        source_type="statute",
        source_id="009682",
        version="2020-01-01-17000",
        payload=payload,
        collected_at=collected_at,
    )

    normalized = normalize_documents(data_dir=data_dir)
    assert normalized["created"] == 1

    indexed = rebuild_index(data_dir=data_dir)
    assert indexed["indexed"] == 1

    hits = search_local_index(data_dir=data_dir, query="자동차관리법", limit=5)
    assert len(hits) == 1
    assert hits[0].title == "자동차관리법"


def test_sync_source_statute_writes_snapshot_and_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_dir = tmp_path / "data"

    response = LawSearchResponse(
        query="자동차",
        section="법령명",
        total_count=1,
        page=1,
        results=[
            LawSearchResult(
                law_id="009682",
                title="자동차관리법",
                short_title=None,
                revision_name=None,
                ministry_name="국토교통부",
                promulgation_date="2020-01-01",
                enforcement_date="2020-07-01",
                promulgation_number="17000",
                doc_type_name="법률",
                detail_link=None,
                serial_number="1",
                raw={},
            )
        ],
        raw={},
    )

    detail = LawDetailResponse(
        law_id="009682",
        title="자동차관리법",
        short_title=None,
        promulgation_date="2020-01-01",
        enforcement_date="2020-07-01",
        promulgation_number="17000",
        doc_type="법률",
        ministry="국토교통부",
        language="KO",
        articles=[],
        raw={},
    )

    monkeypatch.setattr(
        "law_shared.legal_tools.file_sync.search_law",
        lambda **_: response,
    )
    monkeypatch.setattr(
        "law_shared.legal_tools.file_sync.fetch_law_detail",
        lambda **_: detail,
    )

    result = sync_source(
        source_type="statute",
        data_dir=data_dir,
        query="자동차",
        start_page=1,
        max_pages=1,
        display=10,
    )
    assert result["saved_count"] == 1

    snapshots = list((raw_root(data_dir) / "statute").rglob("*.json"))
    assert len(snapshots) == 1
    state = load_sync_state(data_dir)
    assert state["sources"]["statute"]["last_saved_count"] == 1


def test_keyword_search_uses_local_index_first(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local_hit = FileSearchHit(
        doc_id="law_go_kr:statute:009682:v1",
        title="자동차관리법",
        score=0.1,
        snippet="로컬 인덱스 결과",
        source_type="statute",
        source_path="/tmp/doc.json",
    )
    monkeypatch.setattr(
        "law_shared.legal_tools.agent_graph.search_local_index",
        lambda **_: [local_hit],
    )

    def _should_not_call(*_: object, **__: object) -> object:
        raise AssertionError("OpenSearch fallback should not be called")

    monkeypatch.setattr(
        "law_shared.legal_tools.agent_graph.search_opensearch",
        _should_not_call,
    )

    hits = tool_keyword_search(query="자동차", k=5, data_dir=tmp_path)
    assert len(hits) == 1
    assert hits[0].doc_id == local_hit.doc_id
    assert hits[0].snippet == "로컬 인덱스 결과"

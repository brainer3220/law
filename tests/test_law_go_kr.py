from __future__ import annotations

import json
from typing import Any

import pytest

from packages.legal_tools.law_go_kr import (
    LAW_GO_KR_OC_ENV,
    LawSearchResponse,
    LawSearchResult,
    search_law,
)
from packages.legal_tools.agent_graph import tool_law_go_search


class _FakeHeaders:
    def __init__(self, charset: str | None = "utf-8") -> None:
        self._charset = charset

    def get_content_charset(self) -> str | None:  # pragma: no cover - interface
        return self._charset


class _FakeResponse:
    def __init__(self, payload: Any, *, status: int = 200) -> None:
        self._payload = payload
        self.status = status
        self.headers = _FakeHeaders()

    def read(self) -> bytes:  # pragma: no cover - simple
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":  # pragma: no cover - simple
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - simple
        return None


def test_search_law_parses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = {
        "LawSearch": {
            "target": "law",
            "키워드": "자동차관리법",
            "section": "법령명",
            "totalCnt": 2,
            "page": 1,
            "law": [
                {
                    "법령ID": 14432,
                    "법령일련번호": "001",
                    "법령명한글": "자동차관리법",
                    "법령약칭명": "자동차법",
                    "제개정구분명": "일부개정",
                    "소관부처명": "국토교통부",
                    "공포일자": "20200101",
                    "시행일자": "20200701",
                    "공포번호": "17000",
                    "법령구분명": "법률",
                    "법령상세링크": "http://www.law.go.kr/link?DOC_ID=14432",
                },
                {
                    "법령ID": 20000,
                    "법령명한글": "자동차손해배상 보장법",
                    "소관부처명": "금융위원회",
                },
            ],
        }
    }

    monkeypatch.setenv(LAW_GO_KR_OC_ENV, "tester")

    def fake_urlopen(req, timeout):  # type: ignore[no-untyped-def]
        assert "OC=tester" in req.full_url
        return _FakeResponse(sample)

    monkeypatch.setattr("packages.legal_tools.law_go_kr.request.urlopen", fake_urlopen)

    response = search_law(query="자동차관리법", display=5)
    assert isinstance(response, LawSearchResponse)
    assert response.query == "자동차관리법"
    assert response.total_count == 2
    assert len(response.results) == 2
    first = response.results[0]
    assert isinstance(first, LawSearchResult)
    assert first.title == "자동차관리법"
    assert first.promulgation_date == "2020-01-01"
    assert first.enforcement_date == "2020-07-01"
    assert first.detail_link and "DOC_ID" in first.detail_link


def test_tool_law_go_search_returns_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_response = LawSearchResponse(
        query="자동차관리법",
        section="법령명",
        total_count=1,
        page=1,
        results=[
            LawSearchResult(
                law_id="14432",
                title="자동차관리법",
                short_title="자동차법",
                revision_name="일부개정",
                ministry_name="국토교통부",
                promulgation_date="2020-01-01",
                enforcement_date="2020-07-01",
                promulgation_number="17000",
                doc_type_name="법률",
                detail_link="http://www.law.go.kr/link?DOC_ID=14432",
                serial_number="001",
                raw={"법령ID": "14432"},
            )
        ],
        raw={},
    )

    def fake_search_law(**_: Any) -> LawSearchResponse:
        return fake_response

    monkeypatch.setattr("packages.legal_tools.agent_graph.search_law", fake_search_law)

    response, hits = tool_law_go_search(query="자동차관리법")
    assert response.total_count == 1
    assert len(hits) == 1
    hit = hits[0]
    assert hit.source == "law_api"
    assert "국토교통부" in hit.snippet
    assert "상세:" in hit.snippet
*** End of File

from __future__ import annotations

import json
from typing import Any

import pytest

from packages.legal_tools.law_go_kr import (
    LAW_GO_KR_OC_ENV,
    LawDetailArticle,
    LawDetailParagraph,
    LawDetailResponse,
    LawInterpretationDetail,
    LawInterpretationResponse,
    LawInterpretationResult,
    LawSearchResponse,
    LawSearchResult,
    fetch_law_detail,
    fetch_law_interpretation,
    search_law,
    search_law_interpretations,
)
from packages.legal_tools.agent_graph import (
    tool_law_go_detail,
    tool_law_go_interpretation_detail,
    tool_law_go_interpretations,
    tool_law_go_search,
)


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


def test_fetch_law_detail_parses_articles(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = {
        "Law": {
            "법령ID": "009682",
            "법령명_한글": "자동차관리법",
            "공포일자": "20200101",
            "시행일자": "20200701",
            "조문": [
                {
                    "조문번호": "제1조",
                    "조문제목": "목적",
                    "조문내용": "이 법은 자동차 ...",
                    "항": [
                        {"항번호": "①", "항내용": "이 법은 자동차를 효율적으로 관리하기 위한 목적이다."}
                    ],
                }
            ],
        }
    }

    monkeypatch.setenv(LAW_GO_KR_OC_ENV, "tester")

    def fake_call_api(*, params, base_url, timeout):  # type: ignore[no-untyped-def]
        assert params["ID"] == "009682"
        return sample

    monkeypatch.setattr("packages.legal_tools.law_go_kr._call_api", fake_call_api)

    detail = fetch_law_detail(law_id="009682")
    assert detail.law_id == "009682"
    assert detail.title == "자동차관리법"
    assert detail.promulgation_date == "2020-01-01"
    assert len(detail.articles) == 1
    article = detail.articles[0]
    assert article.article_no == "제1조"
    assert article.title == "목적"
    assert article.content.startswith("이 법은 자동차")
    assert article.paragraphs and article.paragraphs[0].text.startswith("이 법은 자동차")


def test_tool_law_go_detail_returns_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    detail = LawDetailResponse(
        law_id="009682",
        title="자동차관리법",
        short_title="자동차법",
        promulgation_date="2020-01-01",
        enforcement_date="2020-07-01",
        promulgation_number="17000",
        doc_type="법률",
        ministry="국토교통부",
        language="KO",
        articles=[
            LawDetailArticle(
                article_no="제1조",
                title="목적",
                content="이 법은 자동차를 효율적으로 관리하기 위한 목적이다.",
                enforcement_date="2020-07-01",
                amendment_type="개정",
                paragraphs=[
                    LawDetailParagraph(
                        number="①",
                        text="이 법은 자동차를 효율적으로 관리하기 위한 목적이다.",
                        clause_number=None,
                        clause_text=None,
                        raw={},
                    )
                ],
                raw={},
            )
        ],
        raw={},
    )

    def fake_fetch_law_detail(**_: Any) -> LawDetailResponse:
        return detail

    monkeypatch.setattr("packages.legal_tools.agent_graph.fetch_law_detail", fake_fetch_law_detail)

    response, hits = tool_law_go_detail(law_id="009682")
    assert response.title == "자동차관리법"
    assert len(hits) >= 1
    assert hits[0].source == "law_api"
    assert "목적" in hits[0].snippet


def test_search_law_interpretations_parses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = {
        "LawSearch": {
            "target": "expc",
            "키워드": "자동차",
            "section": "법령해석례명",
            "totalCnt": 1,
            "page": 1,
            "expc": [
                {
                    "법령해석례일련번호": "EXPC001",
                    "안건명": "자동차 관련 질의",
                    "안건번호": "13-0217",
                    "질의기관명": "국토교통부",
                    "회신기관명": "법제처",
                    "회신일자": "20200101",
                    "법령해석례상세링크": "http://www.law.go.kr/expc?case=EXPC001",
                }
            ],
        }
    }

    monkeypatch.setenv(LAW_GO_KR_OC_ENV, "tester")

    def fake_call_api(*, params, base_url, timeout):  # type: ignore[no-untyped-def]
        assert params["target"] == "expc"
        return sample

    monkeypatch.setattr("packages.legal_tools.law_go_kr._call_api", fake_call_api)

    response = search_law_interpretations(query="자동차")
    assert response.total_count == 1
    assert len(response.results) == 1
    result = response.results[0]
    assert result.title == "자동차 관련 질의"
    assert result.case_no == "13-0217"
    assert result.reply_org == "법제처"
    assert result.reply_date == "2020-01-01"


def test_tool_law_go_interpretations_returns_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_response = LawInterpretationResponse(
        query="자동차",
        section="법령해석례명",
        total_count=1,
        page=1,
        results=[
            LawInterpretationResult(
                serial_no="EXPC001",
                title="자동차 관련 질의",
                case_no="13-0217",
                inquiry_org="국토교통부",
                reply_org="법제처",
                reply_date="2020-01-01",
                detail_link="http://www.law.go.kr/expc?case=EXPC001",
                raw={},
            )
        ],
        raw={},
    )

    def fake_search_interpretations(**_: Any) -> LawInterpretationResponse:
        return fake_response

    monkeypatch.setattr(
        "packages.legal_tools.agent_graph.search_law_interpretations",
        fake_search_interpretations,
    )

    response, hits = tool_law_go_interpretations(query="자동차")
    assert response.total_count == 1
    assert len(hits) == 1
    assert hits[0].source == "law_api"
    assert "회신기관" in hits[0].snippet


def test_fetch_law_interpretation_returns_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = {
        "법령해석례일련번호": "EXPC001",
        "안건명": "자동차 관련 질의",
        "안건번호": "13-0217",
        "해석일자": "20200101",
        "해석기관명": "법제처",
        "질의기관명": "국토교통부",
        "질의요지": "자동차 관련 업무 처리 방안",
        "회답": "관련 규정에 따라 처리하십시오.",
        "이유": "법령 해석 결과",
    }

    monkeypatch.setenv(LAW_GO_KR_OC_ENV, "tester")

    def fake_call_api(*, params, base_url, timeout):  # type: ignore[no-untyped-def]
        assert params["target"] == "expc"
        assert params["ID"] == "EXPC001"
        return sample

    monkeypatch.setattr("packages.legal_tools.law_go_kr._call_api", fake_call_api)

    detail = fetch_law_interpretation(interpretation_id="EXPC001")
    assert detail.serial_no == "EXPC001"
    assert detail.title == "자동차 관련 질의"
    assert detail.reply and "처리" in detail.reply


def test_tool_law_go_interpretation_detail_returns_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    detail = LawInterpretationDetail(
        serial_no="EXPC001",
        title="자동차 관련 질의",
        case_no="13-0217",
        interpretation_date="2020-01-01",
        interpretation_org="법제처",
        inquiry_org="국토교통부",
        summary="자동차 관련 업무 처리 방안",
        reply="관련 규정에 따라 처리하십시오.",
        reason="법령 해석 결과",
        raw={},
    )

    def fake_fetch_interpretation(**_: Any) -> LawInterpretationDetail:
        return detail

    monkeypatch.setattr(
        "packages.legal_tools.agent_graph.fetch_law_interpretation",
        fake_fetch_interpretation,
    )

    response, hits = tool_law_go_interpretation_detail(interpretation_id="EXPC001")
    assert response.reply and "처리" in response.reply
    assert len(hits) == 1
    assert hits[0].source == "law_api"
    assert "해석기관" in hits[0].snippet
*** End of File

from __future__ import annotations

from pathlib import Path
import json

from law_shared.legal_tools import agent_graph
from law_shared.legal_tools.agent_graph import (
    EvidenceStore,
    Hit,
    LangChainToolAgent,
    _llm_provider_candidates,
    _keyword_search,
    _should_fallback_provider,
)
from law_shared.legal_tools.api_server import _merge_agent_payload
from law_shared.legal_tools.response_builder import build_legal_answer_payload


def test_build_legal_answer_payload_returns_answer_ready_for_verified_claims() -> None:
    payload = build_legal_answer_payload(
        question="근로시간 면제 관련 판례 알려줘",
        answer="대법원은 근로시간 면제 범위를 엄격하게 봅니다. [1]",
        citations=[
            {
                "rank": 1,
                "doc_id": "2020다12345",
                "title": "대법원 판례",
                "pin_cite": "L10",
                "snippet": "근로시간 면제 범위를 엄격하게 봐야 한다.",
                "source": "keyword",
                "path": "",
            }
        ],
        evidence=[
            {
                "rank": 1,
                "doc_id": "2020다12345",
                "title": "대법원 판례",
                "score": 0.91,
                "snippet": "근로시간 면제 범위를 엄격하게 봐야 한다.",
                "source": "keyword",
                "path": "",
            }
        ],
        queries=["근로시간 면제 판례"],
        actions=[
            {"tool": "keyword_search", "payload": {"query": "근로시간 면제 판례"}}
        ],
        llm_provider="openai:gpt-4o-mini",
    )

    assert payload["answerState"] == "answer-ready"
    assert payload["answer"]
    assert payload["claims"][0]["status"] == "verified"
    assert payload["evidence"][0]["number"] == "2020다12345"
    assert payload["provenance"]["retrievalMethod"] == "keyword_search"


def test_build_legal_answer_payload_returns_refusal_when_claim_has_no_citations() -> (
    None
):
    payload = build_legal_answer_payload(
        question="근로시간 면제 관련 판례 알려줘",
        answer="현재 확보된 근거만으로는 결론을 확정하기 어렵습니다.",
        citations=[],
        evidence=[],
        queries=["근로시간 면제 판례"],
        actions=[],
    )

    assert payload["answerState"] == "refusal-with-next-step"
    assert payload["answer"] is None
    assert payload["reason"]
    assert payload["nextSteps"]
    assert payload["claims"][0]["status"] == "unavailable"


def test_build_legal_answer_payload_returns_answer_limited_for_partial_claims() -> None:
    payload = build_legal_answer_payload(
        question="근로시간 면제 관련 판례 알려줘",
        answer="대법원은 엄격한 해석을 취했습니다. [1][2]",
        citations=[
            {
                "rank": 1,
                "doc_id": "2020다12345",
                "title": "대법원 판례",
                "pin_cite": "L10",
                "snippet": "근로시간 면제 범위를 엄격하게 봐야 한다.",
                "source": "keyword",
                "path": "",
            }
        ],
        evidence=[
            {
                "rank": 1,
                "doc_id": "2020다12345",
                "title": "대법원 판례",
                "score": 0.91,
                "snippet": "근로시간 면제 범위를 엄격하게 봐야 한다.",
                "source": "keyword",
                "path": "",
            }
        ],
        queries=["근로시간 면제 판례"],
        actions=[],
    )

    assert payload["answerState"] == "answer-limited"
    assert payload["claims"][0]["status"] == "partial"
    assert payload["claims"][0]["unsupportedReasons"] == ["일부 인용만 확인되었습니다."]


def test_build_legal_answer_payload_ignores_markdown_headings_without_citations() -> (
    None
):
    payload = build_legal_answer_payload(
        question="근로시간 면제 관련 최신 판례와 법령상 기준을 알려줘",
        answer=(
            "## 근로시간 면제 관련 최신 판례 및 법령상 기준\n\n"
            "### 1. 사건 정보 및 요약\n\n"
            "- **사건명**: 근로시간면제 한도 재설정 질의 [1]\n"
            "- **사건번호**: MEILI-2024-001 [1]\n\n"
            "### 2. 결론\n\n"
            "근로시간면제 한도는 대통령령 상한을 초과할 수 없습니다 [1]."
        ),
        citations=[
            {
                "rank": 1,
                "doc_id": "MEILI-2024-001",
                "title": "근로시간면제 한도 재설정 질의",
                "pin_cite": "p1/1",
                "snippet": "근로시간면제 한도는 대통령령으로 정한 상한을 초과할 수 없습니다.",
                "source": "keyword",
                "path": "data/meilisearch/labor_guidance.json",
            }
        ],
        evidence=[
            {
                "rank": 1,
                "doc_id": "MEILI-2024-001",
                "title": "근로시간면제 한도 재설정 질의",
                "score": 6.0,
                "snippet": "근로시간면제 한도는 대통령령으로 정한 상한을 초과할 수 없습니다.",
                "source": "keyword",
                "path": "data/meilisearch/labor_guidance.json",
            }
        ],
        queries=["근로시간 면제 판례"],
        actions=[
            {"tool": "keyword_search", "payload": {"query": "근로시간 면제 판례"}}
        ],
    )

    assert payload["answerState"] == "answer-ready"
    assert [claim["text"] for claim in payload["claims"]] == [
        "사건명: 근로시간면제 한도 재설정 질의 [1]",
        "사건번호: MEILI-2024-001 [1]",
        "근로시간면제 한도는 대통령령 상한을 초과할 수 없습니다 [1].",
    ]


def test_build_legal_answer_payload_returns_system_error_on_search_failure_without_evidence() -> (
    None
):
    payload = build_legal_answer_payload(
        question="근로시간 면제 관련 판례 알려줘",
        answer="",
        citations=[],
        evidence=[],
        queries=[],
        actions=[],
        search_error="OpenSearch unavailable",
    )

    assert payload["answerState"] == "system-error"
    assert "검색 백엔드" in " ".join(payload["missingEvidence"])


def test_build_legal_answer_payload_downgrades_to_limited_when_error_has_evidence() -> (
    None
):
    payload = build_legal_answer_payload(
        question="근로시간 면제 관련 최신 판례와 법령상 기준을 알려줘",
        answer="근로시간면제 한도는 대통령령 상한을 초과할 수 없습니다 [1].",
        citations=[
            {
                "rank": 1,
                "doc_id": "MEILI-2024-001",
                "title": "근로시간면제 한도 재설정 질의",
                "pin_cite": "p1/1",
                "snippet": "근로시간면제 한도는 대통령령 상한을 초과할 수 없습니다.",
                "source": "keyword",
                "path": "data/meilisearch/labor_guidance.json",
            }
        ],
        evidence=[
            {
                "rank": 1,
                "doc_id": "MEILI-2024-001",
                "title": "근로시간면제 한도 재설정 질의",
                "score": 6.0,
                "snippet": "근로시간면제 한도는 대통령령 상한을 초과할 수 없습니다.",
                "source": "keyword",
                "path": "data/meilisearch/labor_guidance.json",
            }
        ],
        queries=["근로시간 면제 판례"],
        actions=[],
        error="gemini quota exceeded",
    )

    assert payload["answerState"] == "answer-limited"
    assert "검증 엔진 오류" in " ".join(payload["missingEvidence"])


def test_merge_agent_payload_includes_structured_grounding() -> None:
    law_payload = {"checkpoint_id": "chk_123"}
    agent_result = {
        "citations": [{"rank": 1}],
        "evidence": [{"rank": 1, "title": "대법원 판례"}],
        "legal_answer": {"answerState": "answer-ready", "claims": []},
    }

    _merge_agent_payload(law_payload, agent_result)

    assert law_payload["checkpoint_id"] == "chk_123"
    assert law_payload["citations"] == [{"rank": 1}]
    assert law_payload["evidence"][0]["title"] == "대법원 판례"
    assert law_payload["legal_answer"]["answerState"] == "answer-ready"


def test_finalize_preserves_existing_fields_and_adds_legal_answer() -> None:
    agent = LangChainToolAgent.__new__(LangChainToolAgent)
    store = EvidenceStore(top_k=5, context_chars=200)
    store.add_hits(
        [
            Hit(
                source="keyword",
                path=Path("data/cases/sample.json"),
                doc_id="2020다12345",
                title="대법원 판례",
                score=0.93,
                snippet="근로시간 면제 범위를 엄격하게 본다.",
                line_no=12,
            )
        ]
    )
    result = agent._finalize(
        "근로시간 면제 관련 판례 알려줘",
        store,
        "대법원은 근로시간 면제 범위를 엄격하게 봅니다. [1]",
        intermediate_steps=[],
        iters=1,
    )

    assert result["answer"]
    assert result["citations"]
    assert result["evidence"]
    assert result["legal_answer"]["answerState"] == "answer-ready"


def test_keyword_search_falls_back_to_local_meili_guidance(
    tmp_path, monkeypatch
) -> None:
    meili_dir = tmp_path / "meilisearch"
    meili_dir.mkdir(parents=True)
    sample = {
        "info": {
            "doc_id": "MEILI-2024-001",
            "title": "근로시간면제 한도 재설정 질의",
            "summary": "노조 전임자의 근로시간면제 한도 조정 절차에 관한 질의 회신",
            "statutes": ["노동조합 및 노동관계조정법 시행령 제24조"],
        },
        "taskinfo": {
            "instruction": "기존 근로시간면제 한도를 조정하려면 어떤 절차를 거쳐야 하는지 알려 주세요.",
            "output": "근로시간면제 한도는 노사합의를 통해 정할 수 있으나 대통령령 상한을 초과할 수 없습니다.",
        },
    }
    noisy = {
        "info": {
            "doc_id": "MEILI-2024-002",
            "title": "체납 지방세 가산금 면제 여부",
            "summary": "천재지변으로 인한 가산금 면제 가능성 검토",
        },
        "taskinfo": {
            "instruction": "가산금 면제가 가능한지 알려 주세요.",
            "output": "지방세기본법상 가산금 면제 요건을 검토합니다.",
        },
    }
    (meili_dir / "labor_guidance.json").write_text(
        json.dumps(sample, ensure_ascii=False), encoding="utf-8"
    )
    (meili_dir / "tax_penalty.json").write_text(
        json.dumps(noisy, ensure_ascii=False), encoding="utf-8"
    )

    monkeypatch.setattr(agent_graph, "search_opensearch", lambda *args, **kwargs: [])
    monkeypatch.setattr(agent_graph, "_OPENSEARCH_AVAILABLE", True)
    monkeypatch.setattr(agent_graph, "_OPENSEARCH_ERROR", None)

    hits = _keyword_search("근로시간 면제", limit=5, data_dir=tmp_path)

    assert hits, "Local fallback should return hits when OpenSearch is empty"
    assert hits[0].doc_id == "MEILI-2024-001"
    assert "근로시간면제" in hits[0].title
    assert all(hit.doc_id != "MEILI-2024-002" for hit in hits)


def test_evidence_store_reranks_and_filters_irrelevant_hits() -> None:
    store = EvidenceStore(
        top_k=5, context_chars=200, focus_query="근로시간 면제 관련 판례"
    )
    store.add_hits(
        [
            Hit(
                source="keyword",
                path=Path("data/meilisearch/tax_penalty.json"),
                doc_id="MEILI-2024-002",
                title="체납 지방세 가산금 면제 여부",
                score=2.0,
                snippet="지방세기본법상 가산금 면제 요건을 검토합니다.",
            ),
            Hit(
                source="keyword",
                path=Path("data/meilisearch/labor_guidance.json"),
                doc_id="MEILI-2024-001",
                title="근로시간면제 한도 재설정 질의",
                score=6.0,
                snippet="근로시간면제 한도는 대통령령 상한을 초과할 수 없습니다.",
            ),
        ]
    )

    evidence = store.evidence_payload()
    assert [item["doc_id"] for item in evidence] == ["MEILI-2024-001"]


def test_llm_provider_candidates_fallback_to_openai_when_gemini_blocked(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LAW_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")

    providers = _llm_provider_candidates(blocked_providers={"gemini"})

    assert providers == ["openai"]


def test_should_fallback_provider_for_quota_errors() -> None:
    assert _should_fallback_provider(RuntimeError("429 quota exceeded")) is True
    assert (
        _should_fallback_provider(RuntimeError("ResourceExhausted: rate limit")) is True
    )
    assert _should_fallback_provider(RuntimeError("unexpected parser error")) is False

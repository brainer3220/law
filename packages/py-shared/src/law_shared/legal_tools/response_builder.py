from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from law_shared.legal_schemas import (
    AnswerState,
    ClaimVerificationStatus,
    FreshnessStatus,
    LegalAnswerPayload,
    NextStep,
    NextStepType,
    VerificationClaim,
    VerificationEvidence,
    VerificationProvenance,
)

_CLAIM_REF_RE = re.compile(r"\[(\d+)\]")
_STRIP_PREFIX_RE = re.compile(r"^(?:[-*]|\d+[.)]|#{1,6})\s*")
_CASE_HINT_RE = re.compile(r"\d{2,4}[가-힣]\d+")
_STATUTE_HINT_RE = re.compile(r"법|시행령|시행규칙|조례|규칙")
_HEADING_LINE_RE = re.compile(r"^(?:#{1,6}\s*|\d+[.)]\s*)")


def build_legal_answer_payload(
    *,
    question: str,
    answer: str,
    citations: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    queries: Sequence[str],
    actions: Sequence[Mapping[str, Any]],
    llm_provider: str | None = None,
    error: str | None = None,
    search_error: str | None = None,
) -> Dict[str, Any]:
    evidence_items = _build_evidence(citations, evidence)
    evidence_by_rank = {
        item.metadata.get("rank"): item
        for item in evidence_items
        if item.metadata.get("rank") is not None
    }
    claims = _build_claims(answer, evidence_by_rank)
    missing_evidence = _build_missing_evidence(
        claims=claims,
        evidence_items=evidence_items,
        error=error,
        search_error=search_error,
    )
    answer_state = _determine_answer_state(
        claims=claims,
        evidence_items=evidence_items,
        error=error,
        search_error=search_error,
    )
    refusal_reason = None
    final_answer = answer.strip() or None
    if answer_state == AnswerState.refusal_with_next_step:
        final_answer = None
        refusal_reason = _build_refusal_reason(missing_evidence)
    elif answer_state == AnswerState.system_error:
        refusal_reason = (
            error or search_error or "검증 엔진 오류로 답변을 보류했습니다."
        )

    payload = LegalAnswerPayload(
        answerState=answer_state,
        answer=final_answer,
        reason=refusal_reason,
        missingEvidence=missing_evidence,
        nextSteps=_build_next_steps(question, queries, evidence_items, answer_state),
        claims=claims,
        evidence=evidence_items,
        provenance=VerificationProvenance(
            retrievalMethod=_build_retrieval_method(actions),
            verifierVersion="evidence-gated-v1",
            modelVersion=llm_provider,
            promptVersion="unknown",
            indexVersion="unknown",
            policyVersion="unknown",
            timestamp=datetime.now(timezone.utc).isoformat(),
            queries=[str(query).strip() for query in queries if str(query).strip()],
            actions=[dict(action) for action in actions],
        ),
    )
    return payload.model_dump(mode="json")


def _build_evidence(
    citations: Sequence[Mapping[str, Any]], evidence: Sequence[Mapping[str, Any]]
) -> List[VerificationEvidence]:
    score_by_rank = {
        int(item.get("rank")): item.get("score")
        for item in evidence
        if item.get("rank") is not None
    }
    items: List[VerificationEvidence] = []
    for citation in citations:
        rank = int(citation.get("rank") or len(items) + 1)
        path = str(citation.get("path") or "").strip() or None
        source_type = _classify_source_type(
            title=str(citation.get("title") or ""),
            doc_id=str(citation.get("doc_id") or ""),
            source=str(citation.get("source") or ""),
        )
        items.append(
            VerificationEvidence(
                id=f"evidence-{rank}",
                type=source_type,
                title=str(citation.get("title") or "출처 미상"),
                number=str(citation.get("doc_id") or "").strip() or None,
                pinCite=str(citation.get("pin_cite") or "").strip() or None,
                snippet=str(citation.get("snippet") or "").strip(),
                url=path if path and path.startswith(("http://", "https://")) else None,
                confidence=_coerce_float(score_by_rank.get(rank)),
                verificationStatus=ClaimVerificationStatus.verified,
                freshnessStatus=FreshnessStatus.unknown,
                metadata={
                    "rank": rank,
                    "path": path,
                    "source": str(citation.get("source") or ""),
                },
            )
        )
    return items


def _build_claims(
    answer: str, evidence_by_rank: Mapping[int, VerificationEvidence]
) -> List[VerificationClaim]:
    claims: List[VerificationClaim] = []
    for idx, raw_line in enumerate(_extract_claim_lines(answer), start=1):
        refs = [int(match) for match in _CLAIM_REF_RE.findall(raw_line)]
        resolved = [evidence_by_rank[ref] for ref in refs if ref in evidence_by_rank]
        if not refs:
            status = ClaimVerificationStatus.unavailable
            reasons = ["주장에 연결된 인용이 없습니다."]
        elif not resolved:
            status = ClaimVerificationStatus.unavailable
            reasons = ["인용 번호를 근거 목록과 연결하지 못했습니다."]
        elif len(resolved) != len(refs):
            status = ClaimVerificationStatus.partial
            reasons = ["일부 인용만 확인되었습니다."]
        elif any(item.freshnessStatus == FreshnessStatus.stale for item in resolved):
            status = ClaimVerificationStatus.stale
            reasons = ["최신성 확인이 충분하지 않습니다."]
        else:
            status = ClaimVerificationStatus.verified
            reasons = []
        claims.append(
            VerificationClaim(
                id=f"claim-{idx}",
                text=raw_line.strip(),
                citationIndices=refs,
                evidenceIds=[item.id for item in resolved],
                status=status,
                freshnessStatus=_claim_freshness(resolved),
                unsupportedReasons=reasons,
            )
        )
    if claims:
        return claims[:5]
    return [
        VerificationClaim(
            id="claim-1",
            text=(answer or "답변을 생성하지 못했습니다.").strip(),
            citationIndices=[],
            evidenceIds=[],
            status=ClaimVerificationStatus.unavailable,
            freshnessStatus=FreshnessStatus.unknown,
            unsupportedReasons=["검증 가능한 claim을 추출하지 못했습니다."],
        )
    ]


def _extract_claim_lines(answer: str) -> List[str]:
    if not answer.strip():
        return []
    lines = [segment.rstrip() for segment in answer.splitlines()]
    cleaned: List[str] = []
    for original_line in lines:
        line = original_line.strip()
        if not line:
            continue
        raw_heading = bool(_HEADING_LINE_RE.match(line))
        while True:
            stripped = _STRIP_PREFIX_RE.sub("", line).strip()
            if stripped == line:
                break
            line = stripped
        if not line or line in {":", "-"}:
            continue
        if len(line) < 8:
            continue
        if _looks_like_heading(line, raw_heading=raw_heading):
            continue
        cleaned.append(_normalize_claim_text(line))
    if cleaned:
        return cleaned[:5]
    sentences = [segment.strip() for segment in re.split(r"(?<=[.!?]|다\.)\s+", answer)]
    return [_normalize_claim_text(sentence) for sentence in sentences if sentence][:5]


def _looks_like_heading(line: str, *, raw_heading: bool) -> bool:
    if _CLAIM_REF_RE.search(line):
        return False
    compact = re.sub(r"[*_`]+", "", line).strip()
    if raw_heading and len(compact) <= 80:
        return True
    if len(compact) > 60:
        return False
    if re.search(r"[.!?]|다\.$", compact):
        return False
    heading_keywords = (
        "요약",
        "사건 정보",
        "사건정보",
        "법령상 기준",
        "결론",
        "판단",
        "핵심",
        "최신 판례",
    )
    return any(keyword in compact for keyword in heading_keywords)


def _normalize_claim_text(line: str) -> str:
    line = line.replace("**", "").replace("__", "")
    return re.sub(r"\s+", " ", line).strip()


def _determine_answer_state(
    *,
    claims: Sequence[VerificationClaim],
    evidence_items: Sequence[VerificationEvidence],
    error: str | None,
    search_error: str | None,
) -> AnswerState:
    if error and not evidence_items:
        return AnswerState.system_error
    if search_error and not evidence_items:
        return AnswerState.system_error
    if not claims:
        return AnswerState.refusal_with_next_step
    statuses = {claim.status for claim in claims}
    if error and evidence_items:
        return AnswerState.answer_limited
    if statuses == {ClaimVerificationStatus.verified}:
        return AnswerState.answer_ready
    if (
        ClaimVerificationStatus.verified in statuses
        or ClaimVerificationStatus.partial in statuses
        or ClaimVerificationStatus.stale in statuses
    ):
        return AnswerState.answer_limited
    return AnswerState.refusal_with_next_step


def _build_missing_evidence(
    *,
    claims: Sequence[VerificationClaim],
    evidence_items: Sequence[VerificationEvidence],
    error: str | None,
    search_error: str | None,
) -> List[str]:
    issues: List[str] = []
    if error:
        issues.append("검증 엔진 오류가 발생했습니다.")
    if search_error:
        issues.append("검색 백엔드가 불안정합니다.")
    if not evidence_items:
        issues.append("검증 가능한 검색 결과가 없습니다.")
    for claim in claims:
        if claim.status == ClaimVerificationStatus.unavailable:
            issues.extend(claim.unsupportedReasons)
    deduped: List[str] = []
    seen = set()
    for issue in issues:
        if issue in seen:
            continue
        seen.add(issue)
        deduped.append(issue)
    return deduped


def _build_refusal_reason(missing_evidence: Sequence[str]) -> str:
    if missing_evidence:
        return f"검증 가능한 근거가 충분하지 않아 결론형 답변을 제공하지 않았습니다. {missing_evidence[0]}"
    return "검증 가능한 근거가 충분하지 않아 결론형 답변을 제공하지 않았습니다."


def _build_next_steps(
    question: str,
    queries: Sequence[str],
    evidence_items: Sequence[VerificationEvidence],
    answer_state: AnswerState,
) -> List[NextStep]:
    items: List[NextStep] = []
    for query in _dedupe_strings(queries)[:2]:
        items.append(
            NextStep(
                type=NextStepType.query,
                label="확인 가능한 검색어로 다시 찾기",
                value=query,
            )
        )
    if not items and question.strip():
        items.append(
            NextStep(
                type=NextStepType.query,
                label="사건명, 법원명, 조문명을 포함해 다시 검색",
                value=f"{question.strip()} 판례",
            )
        )
    for evidence in evidence_items[:2]:
        items.append(
            NextStep(
                type=NextStepType.source,
                label="확인 가능한 출처 열기",
                value=evidence.title,
            )
        )
    if answer_state == AnswerState.refusal_with_next_step:
        items.append(
            NextStep(
                type=NextStepType.note,
                label="질문을 더 좁히기",
                value="사건번호, 법원, 조문명 중 하나를 추가하면 검증 가능성이 높아집니다.",
            )
        )
    return items[:4]


def _build_retrieval_method(actions: Sequence[Mapping[str, Any]]) -> str:
    tools = []
    for action in actions:
        tool = str(action.get("tool") or "").strip()
        if tool and tool not in tools:
            tools.append(tool)
    return " + ".join(tools) if tools else "keyword_search"


def _claim_freshness(items: Sequence[VerificationEvidence]) -> FreshnessStatus:
    if any(item.freshnessStatus == FreshnessStatus.stale for item in items):
        return FreshnessStatus.stale
    if any(item.freshnessStatus == FreshnessStatus.current for item in items):
        return FreshnessStatus.current
    return FreshnessStatus.unknown


def _classify_source_type(*, title: str, doc_id: str, source: str) -> str:
    haystack = f"{title} {doc_id} {source}"
    if _CASE_HINT_RE.search(haystack) or any(
        token in haystack for token in ("판례", "대법원", "고등법원", "지방법원")
    ):
        return "case"
    if _STATUTE_HINT_RE.search(haystack):
        return "statute"
    return "doc"


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe_strings(values: Iterable[str]) -> List[str]:
    deduped: List[str] = []
    seen = set()
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped

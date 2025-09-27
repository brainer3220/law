from __future__ import annotations

import os
import re
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency fallback
    import structlog
except ImportError:  # pragma: no cover - fallback to stdlib logging
    import logging

    class _StructlogShim:
        def get_logger(self, name: str):  # type: ignore[override]
            return logging.getLogger(name)

    structlog = _StructlogShim()  # type: ignore

try:  # pragma: no cover - optional dependency fallback
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - minimal shim

    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def model_dump(self, *_, **__):
            return self.__dict__.copy()

        @classmethod
        def model_validate(cls, data):
            return data if isinstance(data, cls) else cls(**data)

    def Field(default=None, **kwargs):  # type: ignore
        return default


from typing_extensions import Literal

from packages.legal_tools.law_go_kr import (
    LawDetailArticle,
    LawDetailResponse,
    LawInterpretationDetail,
    LawInterpretationResponse,
    LawInterpretationResult,
    LawSearchError,
    LawSearchResult,
    LawSearchResponse,
    fetch_law_detail,
    fetch_law_interpretation,
    search_law,
    search_law_interpretations,
)
from packages.legal_tools.opensearch_search import OpenSearchDoc, search_opensearch
from packages.legal_tools.tracing import get_langsmith_callbacks, trace_run

logger = structlog.get_logger(__name__)
_LLM_BLOCKED: bool = False
_OPENSEARCH_AVAILABLE: bool = True
_OPENSEARCH_ERROR: Optional[str] = None


_SENSITIVE_DEBUG_KEYWORDS: Tuple[str, ...] = (
    "token",
    "secret",
    "apikey",
    "api_key",
    "password",
    "authorization",
    "auth",
    "credential",
)


def _is_empty_debug_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _sanitize_debug_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(keyword in lowered for keyword in _SENSITIVE_DEBUG_KEYWORDS):
        return "***redacted***"
    return value


def _sanitize_debug_payload(
    payload: Dict[str, Any], *, allow_empty_keys: Tuple[str, ...] = ()
) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        if key not in allow_empty_keys and _is_empty_debug_value(value):
            continue
        sanitized[key] = _sanitize_debug_value(key, value)
    return sanitized


def _debug_params(**kwargs: Any) -> Dict[str, Any]:
    """Drop empty values and redact sensitive tokens to keep debug logs concise."""

    return _sanitize_debug_payload(dict(kwargs))


def _emit_debug_event(
    event: str,
    payload: Dict[str, Any],
    *,
    allow_empty_keys: Tuple[str, ...] = (),
) -> None:
    sanitized = _sanitize_debug_payload(dict(payload), allow_empty_keys=allow_empty_keys)

    debug_enabled = False
    checker = getattr(logger, "isEnabledFor", None)
    if callable(checker):  # structlog stdlib loggers expose this
        try:
            debug_enabled = bool(checker(logging.DEBUG))
        except Exception:
            debug_enabled = False
    else:
        underlying = getattr(logger, "logger", None)
        if underlying is not None and hasattr(underlying, "isEnabledFor"):
            debug_enabled = underlying.isEnabledFor(logging.DEBUG)
        else:
            debug_enabled = logging.getLogger(__name__).isEnabledFor(logging.DEBUG)

    if debug_enabled:
        logger.debug(event, **sanitized)
    else:
        logger.info(event, debug_event=True, **sanitized)


@contextmanager
def _log_tool_call(
    start_event: str,
    *,
    start_payload: Dict[str, Any],
    success_event: str,
    success_payload: Callable[..., Dict[str, Any]],
):
    _emit_debug_event(
        start_event,
        dict(start_payload),
        allow_empty_keys=("query",),
    )

    def _log_success(*args: Any, **kwargs: Any) -> None:
        payload = success_payload(*args, **kwargs)
        _emit_debug_event(
            success_event,
            dict(payload),
            allow_empty_keys=("query",),
        )

    yield _log_success


def _llm_provider() -> str:
    provider = (os.getenv("LAW_LLM_PROVIDER") or "").strip().lower()
    if provider:
        return provider
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return "gemini"
    return "openai"


def _env_true(name: str) -> bool:
    value = os.getenv(name)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _llm_enabled() -> bool:
    if _env_true("LAW_OFFLINE"):
        return False
    if _LLM_BLOCKED:
        return False
    provider = _llm_provider()
    if provider == "gemini":
        return bool(
            os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
    return bool(os.getenv("OPENAI_API_KEY"))


def _block_llm(err: Exception) -> None:
    global _LLM_BLOCKED
    _LLM_BLOCKED = True
    logger.warning("llm_disabled_for_run", reason=str(err))


@dataclass
class Hit:
    """A retrieval hit with minimal fields for synthesis and citation."""

    source: Literal["keyword", "semantic", "law_api"]
    path: Path
    doc_id: str
    title: str
    score: float
    snippet: str
    line_no: Optional[int] = None
    page_index: Optional[int] = None
    page_total: Optional[int] = None


class EvidenceStore:
    """Track tool outputs and normalize them for the agent."""

    def __init__(self, *, top_k: int, context_chars: int) -> None:
        self.top_k = max(1, int(top_k))
        self.context_chars = max(0, int(context_chars))
        self._items: List[Tuple[int, Hit]] = []
        self._seen: set[Tuple[str, str, str]] = set()
        self.queries: List[str] = []
        self.actions: List[Dict[str, Any]] = []

    def record_query(self, query: str) -> None:
        q = query.strip()
        if q:
            self.queries.append(q)

    def record_action(self, tool: str, payload: Dict[str, Any]) -> None:
        self.actions.append({"tool": tool, "payload": payload})

    def add_hits(self, hits: Sequence[Hit]) -> str:
        formatted: List[str] = []
        for hit in hits:
            key = (hit.doc_id, str(hit.path), hit.snippet[:160])
            if key in self._seen:
                continue
            self._seen.add(key)
            idx = len(self._items) + 1
            self._items.append((idx, hit))
            formatted.append(self._format_hit(idx, hit))
        if not formatted:
            return "검색 결과가 없습니다."
        return "\n".join(formatted)

    def _format_hit(self, idx: int, hit: Hit) -> str:
        snippet = re.sub(r"\s+", " ", hit.snippet.strip())
        if len(snippet) > 380:
            snippet = snippet[:377] + "..."
        page_pin = (
            f"p{hit.page_index}/{hit.page_total}"
            if (hit.page_index and hit.page_total)
            else None
        )
        line_pin = f"L{hit.line_no}" if hit.line_no else None
        pin = page_pin or line_pin or "snippet"
        return f"[{idx}] {hit.title} ({hit.doc_id}) {pin}: {snippet}"

    def observations_text(self) -> str:
        lines = [self._format_hit(idx, hit) for idx, hit in self._items[: self.top_k]]
        return "\n".join(lines)

    def citations(self) -> List[Dict[str, Any]]:
        cites: List[Dict[str, Any]] = []
        for idx, hit in self._items[: self.top_k]:
            cites.append(
                {
                    "rank": idx,
                    "doc_id": hit.doc_id,
                    "title": hit.title,
                    "path": str(hit.path) if hit.path else "",
                    "pin_cite": (
                        f"p{hit.page_index}/{hit.page_total}"
                        if (hit.page_index and hit.page_total)
                        else (f"L{hit.line_no}" if hit.line_no else "snippet")
                    ),
                    "snippet": hit.snippet,
                    "source": hit.source,
                }
            )
        return cites

    def evidence_payload(self) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for idx, hit in self._items:
            payload.append(
                {
                    "rank": idx,
                    "doc_id": hit.doc_id,
                    "title": hit.title,
                    "path": str(hit.path) if hit.path else "",
                    "score": hit.score,
                    "snippet": hit.snippet,
                    "source": hit.source,
                    "page_index": hit.page_index,
                    "page_total": hit.page_total,
                    "line_no": hit.line_no,
                }
            )
        return payload

    def total_hits(self) -> int:
        return len(self._items)


class KeywordSearchArgs(BaseModel):
    query: str = Field(..., description="한국어 검색 질의")
    k: Optional[int] = Field(None, description="최대 반환 건수 (기본값: top_k)")
    context_chars: Optional[int] = Field(
        None, description="문맥으로 포함할 본문 길이 (기본값: context_chars)"
    )


class LawSearchArgs(BaseModel):
    query: str = Field(..., description='법령명 검색 질의 (예: "자동차관리법")')
    search: Optional[int] = Field(None, description="검색범위 (1: 법령명, 2: 본문검색)")
    display: Optional[int] = Field(None, description="표시 건수 (1-100)")
    page: Optional[int] = Field(None, description="결과 페이지 (1부터)")
    sort: Optional[str] = Field(
        None,
        description="정렬 옵션 (lasc, ldes, dasc, ddes, nasc, ndes, efasc, efdes)",
    )
    ef_yd: Optional[str] = Field(
        None, description="시행일자 범위 (예: 20090101~20090130)"
    )
    anc_yd: Optional[str] = Field(
        None, description="공포일자 범위 (예: 20090101~20090130)"
    )
    anc_no: Optional[str] = Field(None, description="공포번호 범위 (예: 306~400)")
    rr_cls_cd: Optional[str] = Field(None, description="제개정 구분 코드")
    nb: Optional[int] = Field(None, description="공포번호 검색")
    org: Optional[str] = Field(None, description="소관부처 코드")
    knd: Optional[str] = Field(None, description="법령종류 코드")
    ls_chap_no: Optional[str] = Field(None, description="법령분류 코드")
    gana: Optional[str] = Field(None, description="사전식 검색 (ga, na 등)")
    oc: Optional[str] = Field(
        None, description="law.go.kr OC 값 (기본값: 환경 변수 LAW_GO_KR_OC)"
    )


class LawDetailArgs(BaseModel):
    law_id: Optional[str] = Field(None, description="법령 ID (ID)")
    mst: Optional[str] = Field(None, description="법령 마스터 번호 (MST)")
    lm: Optional[str] = Field(None, description="법령명 (LM)")
    ld: Optional[int] = Field(None, description="공포일자 (YYYYMMDD)")
    ln: Optional[int] = Field(None, description="공포번호")
    jo: Optional[int] = Field(None, description="조번호 (6자리: 조번호+조가지)")
    lang: Optional[str] = Field(None, description="언어 (KO 또는 ORI)")
    oc: Optional[str] = Field(
        None, description="law.go.kr OC 값 (기본값: 환경 변수 LAW_GO_KR_OC)"
    )


class LawInterpretationSearchArgs(BaseModel):
    query: Optional[str] = Field(None, description='법령해석례 검색 질의 (예: "착공")')
    search: Optional[int] = Field(None, description="검색범위 (1: 안건명, 2: 본문)")
    display: Optional[int] = Field(None, description="표시 건수 (1-100)")
    page: Optional[int] = Field(None, description="결과 페이지 (1부터)")
    inq: Optional[str] = Field(None, description="질의기관 코드")
    rpl: Optional[int] = Field(None, description="회신기관 코드")
    gana: Optional[str] = Field(None, description="사전식 검색 (ga, na 등)")
    itmno: Optional[int] = Field(None, description="안건번호 (숫자)")
    reg_yd: Optional[str] = Field(
        None, description="등록일자 범위 (예: 20090101~20090130)"
    )
    expl_yd: Optional[str] = Field(
        None, description="해석일자 범위 (예: 20090101~20090130)"
    )
    sort: Optional[str] = Field(
        None,
        description="정렬 옵션 (lasc, ldes, dasc, ddes, nasc, ndes)",
    )
    oc: Optional[str] = Field(
        None, description="law.go.kr OC 값 (기본값: 환경 변수 LAW_GO_KR_OC)"
    )


class LawInterpretationDetailArgs(BaseModel):
    interpretation_id: Optional[str] = Field(
        None, description="법령해석례 일련번호 (ID)"
    )
    lm: Optional[str] = Field(None, description="법령해석례명 (LM)")
    oc: Optional[str] = Field(
        None, description="law.go.kr OC 값 (기본값: 환경 변수 LAW_GO_KR_OC)"
    )


USE_CASES_MD: str = """
## 변호사가 GPT를 활용하는 주요 사례

1. **문서 작성 및 초안 작성(drafting)**
2. **법률 리서치 및 사례 정리**
3. **계약서 검토 및 위험 분석(contract review / risk assessment)**
4. **클라이언트 커뮤니케이션 / 내부 커뮤니케이션 개선**
5. **예측 및 전략 수립**
6. **업무 효율화(operational tasks)**
"""


def get_lawyer_gpt_use_cases() -> str:
    return USE_CASES_MD


def tool_keyword_search(
    *, query: str, k: int, data_dir: Path, context_chars: int = 0
) -> List[Hit]:
    return _keyword_search(
        query, limit=max(5, k), data_dir=data_dir, context_chars=context_chars
    )


def tool_law_go_search(
    *,
    query: str,
    search: Optional[int] = None,
    display: Optional[int] = None,
    page: Optional[int] = None,
    sort: Optional[str] = None,
    ef_yd: Optional[str] = None,
    anc_yd: Optional[str] = None,
    anc_no: Optional[str] = None,
    rr_cls_cd: Optional[str] = None,
    nb: Optional[int] = None,
    org: Optional[str] = None,
    knd: Optional[str] = None,
    ls_chap_no: Optional[str] = None,
    gana: Optional[str] = None,
    oc: Optional[str] = None,
) -> Tuple[LawSearchResponse, List[Hit]]:
    response = search_law(
        query=query,
        search=search,
        display=display,
        page=page,
        sort=sort,
        ef_yd=ef_yd,
        anc_yd=anc_yd,
        anc_no=anc_no,
        rr_cls_cd=rr_cls_cd,
        nb=nb,
        org=org,
        knd=knd,
        ls_chap_no=ls_chap_no,
        gana=gana,
        oc=oc,
    )
    hits: List[Hit] = []
    for result in response.results:
        hits.append(_law_result_to_hit(result))
    return response, hits


def tool_law_go_detail(
    *,
    law_id: Optional[str] = None,
    mst: Optional[str] = None,
    lm: Optional[str] = None,
    ld: Optional[int] = None,
    ln: Optional[int] = None,
    jo: Optional[int] = None,
    lang: Optional[str] = None,
    oc: Optional[str] = None,
) -> Tuple[LawDetailResponse, List[Hit]]:
    detail = fetch_law_detail(
        law_id=law_id,
        mst=mst,
        lm=lm,
        ld=ld,
        ln=ln,
        jo=jo,
        lang=lang,
        oc=oc,
    )
    hits: List[Hit] = []
    doc_id = detail.law_id or detail.title or "law"
    base_path = Path(f"law/{doc_id}")
    for article in detail.articles[:8]:
        hits.append(_law_article_to_hit(detail, article, base_path))
    if not hits:
        hits.append(_law_metadata_hit(detail, base_path))
    return detail, hits


def tool_law_go_interpretations(
    *,
    query: Optional[str] = None,
    search: Optional[int] = None,
    display: Optional[int] = None,
    page: Optional[int] = None,
    inq: Optional[str] = None,
    rpl: Optional[int] = None,
    gana: Optional[str] = None,
    itmno: Optional[int] = None,
    reg_yd: Optional[str] = None,
    expl_yd: Optional[str] = None,
    sort: Optional[str] = None,
    oc: Optional[str] = None,
) -> Tuple[LawInterpretationResponse, List[Hit]]:
    response = search_law_interpretations(
        query=query,
        search=search,
        display=display,
        page=page,
        inq=inq,
        rpl=rpl,
        gana=gana,
        itmno=itmno,
        reg_yd=reg_yd,
        expl_yd=expl_yd,
        sort=sort,
        oc=oc,
    )
    hits: List[Hit] = []
    for result in response.results:
        hits.append(_law_interpretation_to_hit(result))
    return response, hits


def tool_law_go_interpretation_detail(
    *,
    interpretation_id: Optional[str] = None,
    lm: Optional[str] = None,
    oc: Optional[str] = None,
) -> Tuple[LawInterpretationDetail, List[Hit]]:
    detail = fetch_law_interpretation(
        interpretation_id=interpretation_id,
        lm=lm,
        oc=oc,
    )
    doc_id = detail.serial_no or detail.case_no or detail.title or "interpretation"
    try:
        path = Path(f"interpretations/{doc_id}")
    except Exception:
        path = Path("interpretations")
    snippet = _law_interpretation_detail_snippet(detail)
    hit = Hit(
        source="law_api",
        path=path,
        doc_id=str(doc_id),
        title=detail.title or detail.case_no or str(doc_id),
        score=1.0,
        snippet=snippet,
    )
    return detail, [hit]


def _law_result_to_hit(result: LawSearchResult) -> Hit:
    doc_id = result.law_id or result.serial_number or result.title or "law"
    try:
        path = Path(f"law/{doc_id}")
    except Exception:
        path = Path("law")
    snippet = _law_result_snippet(result)
    return Hit(
        source="law_api",
        path=path,
        doc_id=str(doc_id),
        title=result.title or result.short_title or str(doc_id),
        score=1.0,
        snippet=snippet,
    )


def _law_result_snippet(result: LawSearchResult) -> str:
    parts: List[str] = []
    if result.short_title and result.short_title != result.title:
        parts.append(f"약칭: {result.short_title}")
    if result.doc_type_name:
        parts.append(f"구분: {result.doc_type_name}")
    if result.ministry_name:
        parts.append(f"소관부처: {result.ministry_name}")
    if result.revision_name:
        parts.append(f"제·개정: {result.revision_name}")

    date_parts: List[str] = []
    if result.promulgation_date:
        date_parts.append(f"공포 {result.promulgation_date}")
    if result.enforcement_date:
        date_parts.append(f"시행 {result.enforcement_date}")
    if date_parts:
        parts.append(" / ".join(date_parts))

    if result.promulgation_number:
        parts.append(f"공포번호: {result.promulgation_number}")
    if result.detail_link:
        parts.append(f"상세: {result.detail_link}")

    if not parts:
        return "법령 메타데이터가 제공되지 않았습니다."
    return " | ".join(parts)


def _law_interpretation_to_hit(result: LawInterpretationResult) -> Hit:
    doc_id = result.serial_no or result.case_no or (result.title or "interpretation")
    try:
        path = Path(f"interpretations/{doc_id}")
    except Exception:
        path = Path("interpretations")
    snippet = _law_interpretation_snippet(result)
    title = result.title or result.case_no or doc_id
    return Hit(
        source="law_api",
        path=path,
        doc_id=str(doc_id),
        title=title,
        score=1.0,
        snippet=snippet,
    )


def _law_interpretation_snippet(result: LawInterpretationResult) -> str:
    parts: List[str] = []
    if result.case_no:
        parts.append(f"안건번호: {result.case_no}")
    if result.inquiry_org:
        parts.append(f"질의기관: {result.inquiry_org}")
    if result.reply_org:
        parts.append(f"회신기관: {result.reply_org}")
    if result.reply_date:
        parts.append(f"회신일자: {result.reply_date}")
    if result.detail_link:
        parts.append(f"상세: {result.detail_link}")
    if not parts:
        parts.append("법령해석례 메타데이터가 제공되지 않았습니다.")
    return " | ".join(parts)


def _law_interpretation_detail_snippet(detail: LawInterpretationDetail) -> str:
    parts: List[str] = []
    if detail.case_no:
        parts.append(f"안건번호: {detail.case_no}")
    if detail.interpretation_org:
        parts.append(f"해석기관: {detail.interpretation_org}")
    if detail.interpretation_date:
        parts.append(f"해석일자: {detail.interpretation_date}")
    if detail.summary:
        parts.append(f"질의요지: {detail.summary}")
    if detail.reply:
        parts.append(f"회답: {detail.reply}")
    elif detail.reason:
        parts.append(f"이유: {detail.reason}")
    snippet = " | ".join(parts)
    return (
        snippet[:1200]
        if len(snippet) > 1200
        else snippet or "법령해석례 본문 정보가 제공되지 않았습니다."
    )


def _law_article_to_hit(
    detail: LawDetailResponse, article: LawDetailArticle, base_path: Path
) -> Hit:
    article_id = article.article_no or article.title or "article"
    try:
        path = base_path / f"article-{article_id}"
    except Exception:
        path = base_path
    snippet = _law_article_snippet(article)
    title_parts = [detail.title or detail.short_title or "법령", article.article_no]
    title = " - ".join([part for part in title_parts if part])
    return Hit(
        source="law_api",
        path=path,
        doc_id=str(detail.law_id or detail.title or "law"),
        title=title,
        score=1.0,
        snippet=snippet,
    )


def _law_metadata_hit(detail: LawDetailResponse, base_path: Path) -> Hit:
    snippet = _law_metadata_snippet(detail)
    title = detail.title or detail.short_title or "법령"
    return Hit(
        source="law_api",
        path=base_path,
        doc_id=str(detail.law_id or title or "law"),
        title=title,
        score=1.0,
        snippet=snippet,
    )


def _law_article_snippet(article: LawDetailArticle) -> str:
    parts: List[str] = []
    if article.title:
        parts.append(article.title)
    if article.content:
        parts.append(article.content)
    else:
        paragraph_texts = [
            _combine_clause(paragraph)
            for paragraph in article.paragraphs
            if paragraph.text or paragraph.clause_text
        ]
        if paragraph_texts:
            parts.extend(paragraph_texts[:2])
    if not parts:
        parts.append("조문 내용이 제공되지 않았습니다.")
    return " | ".join(parts)[:1200]


def _combine_clause(paragraph: LawDetailParagraph) -> str:
    clause = paragraph.clause_text or ""
    text = paragraph.text or ""
    if clause and text:
        return f"{clause} — {text}"
    if text:
        return text
    return clause


def _law_metadata_snippet(detail: LawDetailResponse) -> str:
    parts: List[str] = []
    if detail.doc_type:
        parts.append(f"구분: {detail.doc_type}")
    if detail.ministry:
        parts.append(f"소관부처: {detail.ministry}")
    date_parts: List[str] = []
    if detail.promulgation_date:
        date_parts.append(f"공포 {detail.promulgation_date}")
    if detail.enforcement_date:
        date_parts.append(f"시행 {detail.enforcement_date}")
    if date_parts:
        parts.append(" / ".join(date_parts))
    if detail.promulgation_number:
        parts.append(f"공포번호: {detail.promulgation_number}")
    if not parts:
        parts.append("법령 메타데이터가 제공되지 않았습니다.")
    return " | ".join(parts)


def _keyword_search(
    query: str, limit: int, data_dir: Path, *, context_chars: int = 0
) -> List[Hit]:
    global _OPENSEARCH_AVAILABLE, _OPENSEARCH_ERROR
    if not _OPENSEARCH_AVAILABLE:
        if _OPENSEARCH_ERROR:
            logger.debug("search_keyword_skip_opensearch", reason=_OPENSEARCH_ERROR)
        return []

    logger.info("search_keyword_start", query=query, limit=limit, backend="opensearch")
    try:
        docs: List[OpenSearchDoc] = search_opensearch(query, limit=max(5, limit))
    except Exception as exc:
        _OPENSEARCH_AVAILABLE = False
        _OPENSEARCH_ERROR = f"OpenSearch search failed: {exc}"
        logger.warning("search_keyword_opensearch_failed", error=_OPENSEARCH_ERROR)
        return []

    def _paginate_text(
        text: str, page_chars: int = 400, max_pages: int = 3
    ) -> List[str]:
        text = text.strip()
        if len(text) <= page_chars:
            return [text]
        pages: List[str] = []
        start = 0
        for _ in range(max_pages):
            if start >= len(text):
                break
            end = min(len(text), start + page_chars)
            if end < len(text):
                ws = text.rfind(" ", start, end)
                if ws != -1 and ws > start + int(page_chars * 0.5):
                    end = ws
            pages.append(text[start:end].strip())
            start = end
        if start < len(text) and pages:
            pages[-1] = pages[-1] + "..."
        return pages or [text]

    hits: List[Hit] = []
    for doc in docs:
        snippet = doc.snippet or ""
        if context_chars and doc.body:
            ctx = doc.body
            if context_chars > 0 and len(ctx) > context_chars:
                ctx = ctx[: context_chars - 3] + "..."
            snippet = (snippet + "\n" + ctx).strip()

        try:
            path = Path(doc.source_path) if doc.source_path else Path("")
        except Exception:
            path = Path("")
        approx_chars = max(200, min(800, (context_chars or 800) // 2))
        pages = _paginate_text(
            snippet or doc.body or "", page_chars=approx_chars, max_pages=3
        )
        total = len(pages)
        for idx, page_text in enumerate(pages, start=1):
            if len(page_text) > 1200:
                page_text = page_text[:1197] + "..."
            hits.append(
                Hit(
                    source="keyword",
                    path=path,
                    doc_id=doc.doc_id or doc.id,
                    title=doc.title,
                    score=doc.score,
                    snippet=page_text,
                    page_index=idx,
                    page_total=total,
                )
            )
    logger.info("search_keyword_hits", count=len(hits), stage="pre_dedupe")
    return hits


def _is_case_like(hit: Hit) -> bool:
    text = " ".join([hit.title, hit.snippet])
    if re.search(r"대법원|고등법원|판결|판례|주문|이유", text):
        return True
    if re.search(r"\b\d{4}[가-힣]{1}\d{3,6}\b", text):
        return True
    return False


def _dedupe_hits(hits: Iterable[Hit]) -> List[Hit]:
    seen: set = set()
    out: List[Hit] = []
    for hit in hits:
        key = (hit.doc_id, hit.path, hit.snippet[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append(hit)
    return out


def _seed_queries(question: str) -> List[str]:
    q = question.strip()
    out: List[str] = []
    if q:
        out.append(q)
        if "판례" not in q:
            out.append(f"{q} 판례")
    lower = q.replace(" ", "")
    if any(k in lower for k in ["근로시간면제", "근로시간", "면제업무", "타임오프"]):
        out.extend(["근로시간면제", "타임오프", "노조 전임자 근로시간면제"])
    out.extend([f"{q} 대법원", f"{q} 판결"] if q else [])
    seen: set[str] = set()
    uniq: List[str] = []
    for item in out:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            uniq.append(item)
        if len(uniq) >= 5:
            break
    logger.info("seed_queries_selected", queries=uniq)
    return uniq


def _offline_summary(question: str, observations: str) -> str:
    obs = (observations or "").strip()
    if not obs:
        return (
            "# 사건 정보\n(관측된 스니펫 없음 — 사건 정보 제공 불가)\n\n"
            "# 요약\n"
            "관측된 스니펫이 제공되지 않아 근거 기반 요약을 생성할 수 없습니다. 관련 스니펫을 확보하거나 OpenSearch 인덱스를 확인하세요.\n\n"
            "# 법원 판단(핵심)\n"
            "인용할 스니펫이 없어 법원 판단을 제시할 수 없습니다.\n\n"
            "# 결론\n"
            "증거 스니펫이 필요합니다. 스니펫을 제공하거나 데이터 인덱스를 점검하세요. [일반지식]\n\n"
            "# 출처 및 메타데이터\n(번호 없음)"
        )
    lines = [ln.strip() for ln in obs.splitlines() if ln.strip()]
    quotes: List[str] = []
    refs: List[int] = []
    for ln in lines:
        if ln.startswith("[") and "]" in ln:
            try:
                num = int(ln[1 : ln.index("]")])
                refs.append(num)
            except Exception:
                pass
        quotes.append(ln)
        if len(quotes) >= 2:
            break
    ref_list = ", ".join(f"[{n}]" for n in sorted(set(refs))[:5]) or "(번호 없음)"
    q1 = quotes[0] if quotes else ""
    q2 = quotes[1] if len(quotes) > 1 else ""
    body = (
        "# 사건 정보\n(스니펫 기반; 추가 메타데이터 미상)\n\n"
        "# 요약\n"
        "관측된 스니펫을 바탕으로 핵심을 간단히 정리합니다. 상세한 법리 해설은 스니펫 범위 내에서만 제시합니다.\n\n"
        "# 법원 판단(핵심)\n"
    )
    if q1:
        body += f'"{q1}"\n'
    if q2:
        body += f'"{q2}"\n'
    body += (
        "\n# 결론\n"
        "위 스니펫 범위에서 파악되는 내용을 요약했습니다. 추가 근거가 있으면 정확도가 향상됩니다.\n\n"
        "# 출처 및 메타데이터\n"
        f"{ref_list}"
    )
    return body


class LangChainToolAgent:
    """LangChain-based tool calling agent for legal Q&A."""

    def __init__(
        self,
        *,
        data_dir: Path,
        top_k: int,
        max_iters: int,
        allow_general: bool,
        context_chars: int,
    ) -> None:
        self.data_dir = data_dir
        self.top_k = max(1, int(top_k))
        self.max_iters = max(1, int(max_iters))
        self.allow_general = bool(allow_general)
        self.context_chars = int(context_chars)

    def run(self, question: str) -> Dict[str, Any]:
        store = EvidenceStore(top_k=self.top_k, context_chars=self.context_chars)
        cleaned_question = (question or "").strip()
        if not cleaned_question:
            answer = "(질문이 비어있습니다)"
            return self._finalize(
                cleaned_question, store, answer, intermediate_steps=[], iters=0
            )

        provider = _llm_provider()
        logger.info("langchain_agent_provider", provider=provider)
        if not _llm_enabled():
            logger.info(
                "langchain_agent_provider_unavailable",
                provider=provider,
                fallback="deterministic",
            )
            self._bootstrap_offline(cleaned_question, store)
            answer = _offline_summary(cleaned_question, store.observations_text())
            return self._finalize(
                cleaned_question,
                store,
                answer,
                intermediate_steps=[],
                iters=0,
            )

        try:
            result = self._invoke_langchain(cleaned_question, store)
            intermediate_steps = result.get("intermediate_steps", [])
            answer = str(result.get("output", "")).strip()

            if store.total_hits() == 0:
                logger.info("langchain_agent_bootstrap_seed_queries")
                self._bootstrap_offline(cleaned_question, store)
                store.record_action("fallback", {"reason": "no_hits_after_agent"})
            if store.total_hits() == 0:
                answer = _offline_summary(cleaned_question, store.observations_text())
            else:
                if not answer or not self._has_citation(answer):
                    answer = self._summarize_with_llm(
                        cleaned_question, store.observations_text()
                    )

            return self._finalize(
                cleaned_question,
                store,
                answer,
                intermediate_steps=intermediate_steps,
                iters=len(intermediate_steps),
            )
        except Exception as exc:
            logger.exception("langchain_agent_failed", fallback="offline_summary")
            _block_llm(exc)
            if store.total_hits() == 0:
                self._bootstrap_offline(cleaned_question, store)
            answer = _offline_summary(cleaned_question, store.observations_text())
            return self._finalize(
                cleaned_question,
                store,
                answer,
                intermediate_steps=[],
                iters=0,
                error=str(exc),
            )

    def _finalize(
        self,
        question: str,
        store: EvidenceStore,
        answer: str,
        *,
        intermediate_steps: Sequence[Any],
        iters: int,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "question": question,
            "answer": self._append_search_note(answer),
            "citations": store.citations(),
            "evidence": store.evidence_payload(),
            "observations": store.observations_text(),
            "queries": list(store.queries),
            "used_queries": list(store.queries),
            "actions": list(store.actions),
            "iters": iters,
            "done": True,
            "intermediate_steps": list(intermediate_steps),
            **({"error": error} if error else {}),
            **({"search_error": _OPENSEARCH_ERROR} if _OPENSEARCH_ERROR else {}),
            "llm_provider": _llm_provider(),
        }

    def _append_search_note(self, answer: str) -> str:
        text = answer or "(LLM 응답이 비어있습니다)"
        if not text.strip():
            text = "(LLM 응답이 비어있습니다)"
        if _OPENSEARCH_ERROR and "OpenSearch" not in text:
            text = (
                text
                + "\n\n> 참고: OpenSearch 검색 백엔드를 사용할 수 없어 로컬 스니펫을 찾지 못했습니다. "
                + _OPENSEARCH_ERROR
            )
        return text

    def _has_citation(self, answer: str) -> bool:
        return bool(re.search(r"\[\d+\]", answer or ""))

    def _bootstrap_offline(self, question: str, store: EvidenceStore) -> None:
        seeds = _seed_queries(question) or ([question] if question else [])
        for q in seeds[:3]:
            store.record_query(q)
            try:
                hits = tool_keyword_search(
                    query=q,
                    k=max(self.top_k, 5),
                    data_dir=self.data_dir,
                    context_chars=self.context_chars,
                )
            except Exception as exc:
                logger.exception("offline_bootstrap_failed", query=q)
                store.record_action("keyword_search", {"query": q, "error": str(exc)})
                continue
            hits = _dedupe_hits(hits)
            formatted = store.add_hits(hits)
            store.record_action("keyword_search", {"query": q, "note": formatted[:200]})
            if not _OPENSEARCH_AVAILABLE:
                # OpenSearch backend disabled; no point continuing additional queries
                if _OPENSEARCH_ERROR:
                    store.record_action(
                        "keyword_search",
                        {"query": q, "backend_disabled": _OPENSEARCH_ERROR},
                    )
                break

    def _invoke_langchain(self, question: str, store: EvidenceStore) -> Dict[str, Any]:
        from langchain.agents import AgentExecutor, create_tool_calling_agent  # type: ignore
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder  # type: ignore
        from langchain.tools import StructuredTool  # type: ignore

        tools = self._build_tools(store)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
당신은 한국어 법률 리서치 에이전트입니다. 제공된 도구를 사용하여 질문에 대한 근거 기반 답변을 작성하세요.
도구 목록:
- keyword_search: OpenSearch 인덱스를 사용하여 관련 판례/문서를 찾습니다. 반드시 최소 한 번은 사용해야 합니다.
- law_statute_search: law.go.kr 법령 검색 API로 법령명·공포일자 등 메타데이터를 확인합니다.
- law_statute_detail: law.go.kr 법령 본문 조회 API로 특정 조문 내용을 살펴봅니다.
- law_interpretation_search: law.go.kr 법령해석례 검색 API로 질의·회답 사례를 찾습니다.
- law_interpretation_detail: law.go.kr 법령해석례 본문 조회 API로 질의요지와 회답을 확인합니다.
도구는 `[번호]`가 붙은 스니펫을 반환하며, 최종 답변의 모든 주장에는 해당 번호를 인용하세요.
{general_guidance}
불필요한 사설을 피하고, 간결한 마크다운 구조로 사건 정보·요약·법원 판단·결론을 제시하세요.
""".strip(),
                ),
                ("user", "질문: {input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        temperature = 0.0
        try:
            if os.getenv("OPENAI_TEMPERATURE"):
                temperature = float(os.getenv("OPENAI_TEMPERATURE"))
        except Exception:
            temperature = 0.0

        timeout = 30.0
        try:
            if os.getenv("OPENAI_TIMEOUT"):
                timeout = float(os.getenv("OPENAI_TIMEOUT"))
        except Exception:
            timeout = 30.0

        llm = self._create_llm(temperature=temperature, timeout=timeout)

        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=self.max_iters,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            verbose=False,
        )
        inputs = {
            "input": question,
            "general_guidance": self._general_guidance(),
        }
        callbacks = list(get_langsmith_callbacks())
        invoke_config = {"callbacks": callbacks} if callbacks else None
        metadata = {
            "question_preview": question[:200],
            "top_k": self.top_k,
            "max_iters": self.max_iters,
            "allow_general": self.allow_general,
            "context_chars": self.context_chars,
            "llm_provider": _llm_provider(),
        }
        with trace_run("law.agent.invoke", metadata=metadata):
            if invoke_config:
                result = executor.invoke(inputs, config=invoke_config)
            else:
                result = executor.invoke(inputs)
        store.record_action(
            "agent", {"intermediate_steps": len(result.get("intermediate_steps", []))}
        )
        return result

    def _build_tools(self, store: EvidenceStore) -> List[Any]:
        from langchain.tools import StructuredTool  # type: ignore

        context_chars_default = self.context_chars or 800

        def keyword_tool(
            query: str, k: Optional[int] = None, context_chars: Optional[int] = None
        ) -> str:
            limit = max(self.top_k, int(k) if k else self.top_k)
            limit = min(max(limit, 3), self.top_k * 3)
            ctx = int(context_chars) if context_chars else context_chars_default
            store.record_query(query)
            try:
                hits = tool_keyword_search(
                    query=query,
                    k=limit,
                    data_dir=self.data_dir,
                    context_chars=ctx,
                )
            except Exception as exc:
                logger.exception("keyword_search_failed", query=query)
                store.record_action(
                    "keyword_search", {"query": query, "error": str(exc)}
                )
                return f"[검색 오류] {exc}"
            hits = _dedupe_hits(hits)
            formatted = store.add_hits(hits)
            store.record_action(
                "keyword_search", {"query": query, "returned": len(hits)}
            )
            return formatted

        def law_search_tool(
            query: str,
            search: Optional[int] = None,
            display: Optional[int] = None,
            page: Optional[int] = None,
            sort: Optional[str] = None,
            ef_yd: Optional[str] = None,
            anc_yd: Optional[str] = None,
            anc_no: Optional[str] = None,
            rr_cls_cd: Optional[str] = None,
            nb: Optional[int] = None,
            org: Optional[str] = None,
            knd: Optional[str] = None,
            ls_chap_no: Optional[str] = None,
            gana: Optional[str] = None,
            oc: Optional[str] = None,
        ) -> str:
            store.record_query(query)
            debug_params = _debug_params(
                search=search,
                display=display,
                page=page,
                sort=sort,
                ef_yd=ef_yd,
                anc_yd=anc_yd,
                anc_no=anc_no,
                rr_cls_cd=rr_cls_cd,
                nb=nb,
                org=org,
                knd=knd,
                ls_chap_no=ls_chap_no,
                gana=gana,
                oc=oc,
            )
            with _log_tool_call(
                "law_go_kr_search_start",
                start_payload={"query": query, "params": debug_params},
                success_event="law_go_kr_search_success",
                success_payload=lambda response, hits: {
                    "query": query,
                    "total": response.total_count,
                    "page": response.page,
                    "returned": len(hits),
                    "params": debug_params,
                },
            ) as log_success:
                try:
                    response, hits = tool_law_go_search(
                        query=query,
                        search=search,
                        display=display,
                        page=page,
                        sort=sort,
                        ef_yd=ef_yd,
                        anc_yd=anc_yd,
                        anc_no=anc_no,
                        rr_cls_cd=rr_cls_cd,
                        nb=nb,
                        org=org,
                        knd=knd,
                        ls_chap_no=ls_chap_no,
                        gana=gana,
                        oc=oc,
                    )
                except LawSearchError as exc:
                    failure_context = _sanitize_debug_payload(
                        {"query": query, "params": debug_params},
                        allow_empty_keys=("query",),
                    )
                    logger.warning(
                        "law_go_kr_search_failed", error=str(exc), **failure_context
                    )
                    store.record_action(
                        "law_go_kr_search", {"query": query, "error": str(exc)}
                    )
                    return f"[법령 검색 오류] {exc}"
                except Exception as exc:
                    failure_context = _sanitize_debug_payload(
                        {"query": query, "params": debug_params},
                        allow_empty_keys=("query",),
                    )
                    logger.exception(
                        "law_go_kr_search_unexpected_error",
                        error=str(exc),
                        **failure_context,
                    )
                    store.record_action(
                        "law_go_kr_search", {"query": query, "error": str(exc)}
                    )
                    return f"[법령 검색 오류] {exc}"

            hits = _dedupe_hits(hits)
            log_success(response, hits)
            formatted = store.add_hits(hits)
            store.record_action(
                "law_go_kr_search",
                {
                    "query": query,
                    "returned": len(hits),
                    "total": response.total_count,
                    "page": response.page,
                },
            )
            return formatted

        def law_detail_tool(
            law_id: Optional[str] = None,
            mst: Optional[str] = None,
            lm: Optional[str] = None,
            ld: Optional[int] = None,
            ln: Optional[int] = None,
            jo: Optional[int] = None,
            lang: Optional[str] = None,
            oc: Optional[str] = None,
        ) -> str:
            debug_params = _debug_params(
                law_id=law_id,
                mst=mst,
                lm=lm,
                ld=ld,
                ln=ln,
                jo=jo,
                lang=lang,
                oc=oc,
            )
            with _log_tool_call(
                "law_go_kr_detail_start",
                start_payload={"params": debug_params},
                success_event="law_go_kr_detail_success",
                success_payload=lambda response, hits: {
                    "law_id": response.law_id,
                    "title": response.title,
                    "returned": len(hits),
                    "params": debug_params,
                },
            ) as log_success:
                try:
                    response, hits = tool_law_go_detail(
                        law_id=law_id,
                        mst=mst,
                        lm=lm,
                        ld=ld,
                        ln=ln,
                        jo=jo,
                        lang=lang,
                        oc=oc,
                    )
                except LawSearchError as exc:
                    failure_context = _sanitize_debug_payload(
                        {"params": debug_params},
                    )
                    logger.warning(
                        "law_go_kr_detail_failed", error=str(exc), **failure_context
                    )
                    store.record_action(
                        "law_go_kr_detail",
                        {
                            "law_id": law_id,
                            "mst": mst,
                            "lm": lm,
                            "error": str(exc),
                        },
                    )
                    return f"[법령 본문 조회 오류] {exc}"
                except Exception as exc:
                    failure_context = _sanitize_debug_payload(
                        {"params": debug_params},
                    )
                    logger.exception(
                        "law_go_kr_detail_unexpected_error",
                        error=str(exc),
                        **failure_context,
                    )
                    store.record_action(
                        "law_go_kr_detail",
                        {
                            "law_id": law_id,
                            "mst": mst,
                            "lm": lm,
                            "error": str(exc),
                        },
                    )
                    return f"[법령 본문 조회 오류] {exc}"

            hits = _dedupe_hits(hits)
            log_success(response, hits)
            formatted = store.add_hits(hits)
            store.record_action(
                "law_go_kr_detail",
                {
                    "law_id": response.law_id,
                    "title": response.title,
                    "articles": len(response.articles),
                },
            )
            return formatted

        def law_interpretation_tool(
            query: Optional[str] = None,
            search: Optional[int] = None,
            display: Optional[int] = None,
            page: Optional[int] = None,
            inq: Optional[str] = None,
            rpl: Optional[int] = None,
            gana: Optional[str] = None,
            itmno: Optional[int] = None,
            reg_yd: Optional[str] = None,
            expl_yd: Optional[str] = None,
            sort: Optional[str] = None,
            oc: Optional[str] = None,
        ) -> str:
            store.record_query(query or "")
            debug_params = _debug_params(
                search=search,
                display=display,
                page=page,
                inq=inq,
                rpl=rpl,
                gana=gana,
                itmno=itmno,
                reg_yd=reg_yd,
                expl_yd=expl_yd,
                sort=sort,
                oc=oc,
            )
            with _log_tool_call(
                "law_go_kr_interpretation_search_start",
                start_payload={"query": query, "params": debug_params},
                success_event="law_go_kr_interpretation_search_success",
                success_payload=lambda response, hits: {
                    "query": query,
                    "total": response.total_count,
                    "page": response.page,
                    "returned": len(hits),
                    "params": debug_params,
                },
            ) as log_success:
                try:
                    response, hits = tool_law_go_interpretations(
                        query=query,
                        search=search,
                        display=display,
                        page=page,
                        inq=inq,
                        rpl=rpl,
                        gana=gana,
                        itmno=itmno,
                        reg_yd=reg_yd,
                        expl_yd=expl_yd,
                        sort=sort,
                        oc=oc,
                    )
                except LawSearchError as exc:
                    failure_context = _sanitize_debug_payload(
                        {"query": query, "params": debug_params},
                        allow_empty_keys=("query",),
                    )
                    logger.warning(
                        "law_go_kr_interpretation_search_failed",
                        error=str(exc),
                        **failure_context,
                    )
                    store.record_action(
                        "law_go_kr_interpretation", {"query": query, "error": str(exc)}
                    )
                    return f"[법령해석례 검색 오류] {exc}"
                except Exception as exc:
                    failure_context = _sanitize_debug_payload(
                        {"query": query, "params": debug_params},
                        allow_empty_keys=("query",),
                    )
                    logger.exception(
                        "law_go_kr_interpretation_unexpected_error",
                        error=str(exc),
                        **failure_context,
                    )
                    store.record_action(
                        "law_go_kr_interpretation", {"query": query, "error": str(exc)}
                    )
                    return f"[법령해석례 검색 오류] {exc}"

            hits = _dedupe_hits(hits)
            log_success(response, hits)
            formatted = store.add_hits(hits)
            store.record_action(
                "law_go_kr_interpretation",
                {
                    "query": query,
                    "returned": len(hits),
                    "total": response.total_count,
                    "page": response.page,
                },
            )
            return formatted

        def law_interpretation_detail_tool(
            interpretation_id: Optional[str] = None,
            lm: Optional[str] = None,
            oc: Optional[str] = None,
        ) -> str:
            debug_params = _debug_params(
                interpretation_id=interpretation_id,
                lm=lm,
                oc=oc,
            )
            with _log_tool_call(
                "law_go_kr_interpretation_detail_start",
                start_payload={"params": debug_params},
                success_event="law_go_kr_interpretation_detail_success",
                success_payload=lambda detail, hits: {
                    "interpretation_id": detail.serial_no,
                    "title": detail.title,
                    "returned": len(hits),
                    "params": debug_params,
                },
            ) as log_success:
                try:
                    detail, hits = tool_law_go_interpretation_detail(
                        interpretation_id=interpretation_id,
                        lm=lm,
                        oc=oc,
                    )
                except LawSearchError as exc:
                    failure_context = _sanitize_debug_payload(
                        {"params": debug_params},
                    )
                    logger.warning(
                        "law_go_kr_interpretation_detail_failed",
                        error=str(exc),
                        **failure_context,
                    )
                    store.record_action(
                        "law_go_kr_interpretation_detail",
                        {
                            "interpretation_id": interpretation_id,
                            "lm": lm,
                            "error": str(exc),
                        },
                    )
                    return f"[법령해석례 본문 조회 오류] {exc}"
                except Exception as exc:
                    failure_context = _sanitize_debug_payload(
                        {"params": debug_params},
                    )
                    logger.exception(
                        "law_go_kr_interpretation_detail_unexpected_error",
                        error=str(exc),
                        **failure_context,
                    )
                    store.record_action(
                        "law_go_kr_interpretation_detail",
                        {
                            "interpretation_id": interpretation_id,
                            "lm": lm,
                            "error": str(exc),
                        },
                    )
                    return f"[법령해석례 본문 조회 오류] {exc}"

            hits = _dedupe_hits(hits)
            log_success(detail, hits)
            formatted = store.add_hits(hits)
            store.record_action(
                "law_go_kr_interpretation_detail",
                {
                    "interpretation_id": detail.serial_no,
                    "title": detail.title,
                    "has_reply": bool(detail.reply),
                },
            )
            return formatted

        return [
            StructuredTool.from_function(
                keyword_tool,
                name="keyword_search",
                args_schema=KeywordSearchArgs,
                description="OpenSearch 법률 검색. 판례나 행정해석을 찾을 때 사용",
            ),
            StructuredTool.from_function(
                law_search_tool,
                name="law_statute_search",
                args_schema=LawSearchArgs,
                description="law.go.kr 법령 검색 API. 법령명, 공포일자 등 메타데이터 조회",
            ),
            StructuredTool.from_function(
                law_detail_tool,
                name="law_statute_detail",
                args_schema=LawDetailArgs,
                description="law.go.kr 법령 본문 조회 API. 특정 법령의 조문 내용을 확인",
            ),
            StructuredTool.from_function(
                law_interpretation_tool,
                name="law_interpretation_search",
                args_schema=LawInterpretationSearchArgs,
                description="law.go.kr 법령해석례 검색 API. 질의/회신 사례 검색",
            ),
            StructuredTool.from_function(
                law_interpretation_detail_tool,
                name="law_interpretation_detail",
                args_schema=LawInterpretationDetailArgs,
                description="law.go.kr 법령해석례 본문 조회 API. 질의요지·회답 확인",
            ),
        ]

    def _general_guidance(self) -> str:
        if self.allow_general:
            return "스니펫이 부족하면 최소한의 일반 법률 상식을 보충하되, 근거가 없는 문장에는 [일반지식]을 명시하세요."
        return "근거가 부족하면 추가 검색을 통해 [번호] 스니펫을 확보하세요."

    def _create_llm(self, *, temperature: float, timeout: float):  # noqa: ANN001 - LangChain types
        provider = _llm_provider()
        if provider == "gemini":
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "LangChain Gemini backend requires `langchain-google-genai`. Install it with `uv pip install langchain-google-genai`."
                ) from exc

            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            kwargs: Dict[str, Any] = {
                "model": model,
                "temperature": temperature,
                "streaming": False,
                "convert_system_message_to_human": True,
            }
            max_output = os.getenv("GEMINI_MAX_OUTPUT_TOKENS")
            if max_output:
                try:
                    kwargs["max_output_tokens"] = int(max_output)
                except ValueError:
                    logger.warning(
                        "gemini_max_output_tokens_invalid", raw_value=max_output
                    )
            logger.info("langchain_agent_gemini", model=model, temperature=temperature)
            return ChatGoogleGenerativeAI(**kwargs)

        try:
            from langchain_openai import ChatOpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "LangChain OpenAI backend requires `langchain-openai`. Install it with `uv pip install langchain-openai`."
            ) from exc

        model = os.getenv("OPENAI_MODEL", "gpt-5-mini-2025-08-07")
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_retries=1,
            timeout=timeout,
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=False,
            model_kwargs={"stream": False},
        )
        logger.info("langchain_agent_openai", model=model, temperature=temperature)
        return llm

    def _summarize_with_llm(self, question: str, observations: str) -> str:
        if not observations.strip():
            return _offline_summary(question, observations)
        if not _llm_enabled():
            return _offline_summary(question, observations)
        try:
            llm = self._create_llm(
                temperature=0.0,
                timeout=30.0,
            )
        except Exception as exc:  # pragma: no cover - optional dependency path
            logger.warning("langchain_agent_summarize_fallback", error=str(exc))
            _block_llm(exc if isinstance(exc, Exception) else Exception(str(exc)))
            return _offline_summary(question, observations)

        from langchain.prompts import ChatPromptTemplate  # type: ignore

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
당신은 법률 리서치 요약가입니다. 주어진 스니펫만 근거로 한국어 요약을 작성하세요.
- 사건 정보, 요약, 법원 판단(핵심), 결론, 출처 및 메타데이터 순으로 마크다운 섹션을 구성합니다.
- 각 주장에는 [번호] 형태의 인용을 포함합니다.
- 근거가 부족하면 간단히 한계를 언급하세요.
""".strip(),
                ),
                (
                    "user",
                    "질문: {question}\n\n스니펫:\n{observations}\n\n지침: {guidance}",
                ),
            ]
        )

        chain = prompt | llm  # type: ignore
        try:
            output = chain.invoke(
                {
                    "question": question,
                    "observations": observations,
                    "guidance": self._general_guidance(),
                }
            )
        except Exception as exc:  # pragma: no cover - runtime failure
            logger.warning("langchain_agent_summarize_invoke_failed", error=str(exc))
            _block_llm(exc)
            return _offline_summary(question, observations)

        if isinstance(output, str):
            return output.strip()
        content = getattr(output, "content", None)
        if isinstance(content, str):
            return content.strip()
        return str(output)


def build_legal_ask_graph(
    *,
    data_dir: Path,
    top_k: int = 5,
    max_iters: int = 3,
    allow_general: bool = False,
    context_chars: int = 0,
):
    agent = LangChainToolAgent(
        data_dir=data_dir,
        top_k=top_k,
        max_iters=max_iters,
        allow_general=allow_general,
        context_chars=context_chars,
    )

    class _Adapter:
        def invoke(
            self, state: Dict[str, Any], config: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            question = state.get("question", "") if isinstance(state, dict) else ""
            return agent.run(question)

    logger.info(
        "langchain_tool_agent_ready",
        top_k=top_k,
        max_iters=max_iters,
        allow_general=allow_general,
        context_chars=context_chars,
    )
    return _Adapter()


def run_ask(
    question: str,
    *,
    data_dir: Path,
    top_k: int = 5,
    max_iters: int = 3,
    allow_general: bool = False,
    context_chars: int = 0,
) -> Dict[str, Any]:
    context = context_chars or 800
    agent = LangChainToolAgent(
        data_dir=data_dir,
        top_k=top_k,
        max_iters=max_iters,
        allow_general=allow_general,
        context_chars=context,
    )
    metadata = {
        "question_preview": (question or "").strip()[:200],
        "top_k": top_k,
        "max_iters": max_iters,
        "allow_general": allow_general,
        "context_chars": context,
    }
    logger.info("run_ask_start", **metadata)
    with trace_run("law.run_ask", metadata=metadata):
        final = agent.run(question)
    logger.info("run_ask_complete", keys=sorted(final.keys()))
    return final

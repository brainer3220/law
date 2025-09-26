from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib import error, parse, request

try:  # pragma: no cover - optional dependency fallback
    import structlog
except Exception:  # pragma: no cover - fallback to stdlib logging
    import logging

    class _StructlogShim:
        def get_logger(self, name: str):  # type: ignore[override]
            return logging.getLogger(name)

    structlog = _StructlogShim()  # type: ignore

LAW_GO_KR_BASE_URL = "http://www.law.go.kr/DRF/lawSearch.do"
LAW_GO_KR_DETAIL_URL = "http://www.law.go.kr/DRF/lawService.do"
LAW_GO_KR_OC_ENV = "LAW_GO_KR_OC"
SENSITIVE_PARAM_KEYS: frozenset[str] = frozenset({"OC", "password", "secret", "token", "api_key"})
MASKED_SECRET = "********"
LAW_ENTRY_KEYS: frozenset[str] = frozenset({"법령명한글", "법령명", "lawId"})
INTERPRETATION_ENTRY_KEYS: frozenset[str] = frozenset({"법령해석례일련번호", "serialNo", "expcId"})
INTERPRETATION_TITLE_KEYS: frozenset[str] = frozenset({"안건명", "title"})


logger = structlog.get_logger(__name__)


@dataclass
class LawSearchResult:
    law_id: str
    title: str
    short_title: Optional[str]
    revision_name: Optional[str]
    ministry_name: Optional[str]
    promulgation_date: Optional[str]
    enforcement_date: Optional[str]
    promulgation_number: Optional[str]
    doc_type_name: Optional[str]
    detail_link: Optional[str]
    serial_number: Optional[str]
    raw: Dict[str, Any]


@dataclass
class LawSearchResponse:
    query: Optional[str]
    section: Optional[str]
    total_count: Optional[int]
    page: Optional[int]
    results: List[LawSearchResult]
    raw: Dict[str, Any]


class LawSearchError(RuntimeError):
    """Raised when the law.go.kr search API returns an error."""


@dataclass
class LawInterpretationResult:
    serial_no: Optional[str]
    title: Optional[str]
    case_no: Optional[str]
    inquiry_org: Optional[str]
    reply_org: Optional[str]
    reply_date: Optional[str]
    detail_link: Optional[str]
    raw: Dict[str, Any]


@dataclass
class LawInterpretationResponse:
    query: Optional[str]
    section: Optional[str]
    total_count: Optional[int]
    page: Optional[int]
    results: List[LawInterpretationResult]
    raw: Dict[str, Any]


@dataclass
class LawInterpretationDetail:
    serial_no: Optional[str]
    title: Optional[str]
    case_no: Optional[str]
    interpretation_date: Optional[str]
    interpretation_org: Optional[str]
    inquiry_org: Optional[str]
    summary: Optional[str]
    reply: Optional[str]
    reason: Optional[str]
    raw: Dict[str, Any]


@dataclass
class LawDetailParagraph:
    number: Optional[str]
    text: Optional[str]
    clause_number: Optional[str]
    clause_text: Optional[str]
    raw: Dict[str, Any]


@dataclass
class LawDetailArticle:
    article_no: Optional[str]
    title: Optional[str]
    content: Optional[str]
    enforcement_date: Optional[str]
    amendment_type: Optional[str]
    paragraphs: List[LawDetailParagraph]
    raw: Dict[str, Any]


@dataclass
class LawDetailResponse:
    law_id: Optional[str]
    title: Optional[str]
    short_title: Optional[str]
    promulgation_date: Optional[str]
    enforcement_date: Optional[str]
    promulgation_number: Optional[str]
    doc_type: Optional[str]
    ministry: Optional[str]
    language: Optional[str]
    articles: List[LawDetailArticle]
    raw: Dict[str, Any]


def search_law(
    *,
    query: Optional[str] = None,
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
    timeout: float = 10.0,
    base_url: str = LAW_GO_KR_BASE_URL,
) -> LawSearchResponse:
    """Call the law.go.kr search API and return parsed results."""

    resolved_oc = _resolve_oc(oc)
    params: Dict[str, Any] = {"OC": resolved_oc, "target": "law", "type": "JSON"}

    if query:
        params["query"] = query
    if search:
        params["search"] = int(search)
    if display:
        params["display"] = max(1, min(100, int(display)))
    if page:
        params["page"] = max(1, int(page))
    if sort:
        params["sort"] = sort
    if ef_yd:
        params["efYd"] = ef_yd
    if anc_yd:
        params["ancYd"] = anc_yd
    if anc_no:
        params["ancNo"] = anc_no
    if rr_cls_cd:
        params["rrClsCd"] = rr_cls_cd
    if nb:
        params["nb"] = int(nb)
    if org:
        params["org"] = org
    if knd:
        params["knd"] = knd
    if ls_chap_no:
        params["lsChapNo"] = ls_chap_no
    if gana:
        params["gana"] = gana

    data = _call_api(params=params, base_url=base_url, timeout=timeout)
    entries = _collect_entries(data)
    results: List[LawSearchResult] = []
    seen_ids: set[str] = set()
    for entry in entries:
        law_id = _first_str(entry, ["법령ID", "lawId", "LAW_ID", "법령일련번호"]) or ""
        if not law_id:
            law_id = _first_str(entry, ["법령명한글", "법령명"]) or "unknown"
        if law_id in seen_ids:
            continue
        seen_ids.add(law_id)
        result = LawSearchResult(
            law_id=law_id,
            title=_first_str(entry, ["법령명한글", "법령명", "title"]) or law_id,
            short_title=_first_str(entry, ["법령약칭명", "약칭", "shortTitle"]),
            revision_name=_first_str(entry, ["제개정구분명", "revisionCls"]),
            ministry_name=_first_str(entry, ["소관부처명", "부처명", "ministry"]),
            promulgation_date=_format_date(_first_str(entry, ["공포일자", "promulgationDate"])),
            enforcement_date=_format_date(_first_str(entry, ["시행일자", "enforcementDate"])),
            promulgation_number=_first_str(entry, ["공포번호", "promulgationNumber"]),
            doc_type_name=_first_str(entry, ["법령구분명", "docCls"]),
            detail_link=_first_str(entry, ["법령상세링크", "detailLink"]),
            serial_number=_first_str(entry, ["법령일련번호", "serialNo"]),
            raw=entry,
        )
        results.append(result)

    response = LawSearchResponse(
        query=_first_str(data, ["키워드", "keyword"]),
        section=_first_str(data, ["section"]),
        total_count=_first_int(data, ["totalCnt", "total"]),
        page=_first_int(data, ["page"]),
        results=results,
        raw=data,
    )
    return response


def search_law_interpretations(
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
    timeout: float = 10.0,
    base_url: str = LAW_GO_KR_BASE_URL,
) -> LawInterpretationResponse:
    """Search law.go.kr for legal interpretation cases (법령해석례)."""

    resolved_oc = _resolve_oc(oc)
    params: Dict[str, Any] = {"OC": resolved_oc, "target": "expc", "type": "JSON"}

    if query:
        params["query"] = query
    if search:
        params["search"] = int(search)
    if display:
        params["display"] = max(1, min(100, int(display)))
    if page:
        params["page"] = max(1, int(page))
    if inq:
        params["inq"] = inq
    if rpl:
        params["rpl"] = int(rpl)
    if gana:
        params["gana"] = gana
    if itmno:
        params["itmno"] = int(itmno)
    if reg_yd:
        params["regYd"] = reg_yd
    if expl_yd:
        params["explYd"] = expl_yd
    if sort:
        params["sort"] = sort

    data = _call_api(params=params, base_url=base_url, timeout=timeout)
    entries = _collect_entries(data)
    results: List[LawInterpretationResult] = []
    seen_ids: set[str] = set()
    for entry in entries:
        serial_no = _first_str(entry, ["법령해석례일련번호", "serialNo", "expcId"])
        key = serial_no or _first_str(entry, ["안건명", "title"]) or ""
        if not key:
            continue
        if key in seen_ids:
            continue
        seen_ids.add(key)
        results.append(
            LawInterpretationResult(
                serial_no=serial_no,
                title=_first_str(entry, ["안건명", "title"]),
                case_no=_first_str(entry, ["안건번호", "caseNo"]),
                inquiry_org=_first_str(entry, ["질의기관명", "inqOrg"]),
                reply_org=_first_str(entry, ["회신기관명", "replyOrg"]),
                reply_date=_format_date(_first_str(entry, ["회신일자", "replyDate"])),
                detail_link=_first_str(entry, ["법령해석례상세링크", "detailLink"]),
                raw=entry,
            )
        )

    return LawInterpretationResponse(
        query=_first_str(data, ["키워드", "keyword"]),
        section=_first_str(data, ["section"]),
        total_count=_first_int(data, ["totalCnt", "total"]),
        page=_first_int(data, ["page"]),
        results=results,
        raw=data,
    )


def fetch_law_detail(
    *,
    law_id: Optional[str] = None,
    mst: Optional[str] = None,
    lm: Optional[str] = None,
    ld: Optional[int] = None,
    ln: Optional[int] = None,
    jo: Optional[int] = None,
    lang: Optional[str] = None,
    oc: Optional[str] = None,
    timeout: float = 10.0,
    base_url: str = LAW_GO_KR_DETAIL_URL,
) -> LawDetailResponse:
    """Fetch law detail (articles) data from law.go.kr API."""

    if not (law_id or mst or lm):
        raise LawSearchError("법령 상세 조회에는 ID, MST, LM 중 최소 하나가 필요합니다.")

    resolved_oc = _resolve_oc(oc)
    params: Dict[str, Any] = {"OC": resolved_oc, "target": "law", "type": "JSON"}

    if law_id:
        params["ID"] = law_id
    if mst:
        params["MST"] = mst
    if lm:
        params["LM"] = lm
    if ld:
        params["LD"] = int(ld)
    if ln:
        params["LN"] = int(ln)
    if jo:
        params["JO"] = int(jo)
    if lang:
        params["LANG"] = lang

    data = _call_api(params=params, base_url=base_url, timeout=timeout)

    response = LawDetailResponse(
        law_id=_first_str(data, ["법령ID", "lawID", "lawId"]),
        title=_first_str(data, ["법령명_한글", "법령명", "lawName"]),
        short_title=_first_str(data, ["법령명약칭", "약칭", "shortTitle"]),
        promulgation_date=_format_date(_first_str(data, ["공포일자", "promulgationDate"])),
        enforcement_date=_format_date(_first_str(data, ["시행일자", "enforcementDate"])),
        promulgation_number=_first_str(data, ["공포번호", "promulgationNumber"]),
        doc_type=_first_str(data, ["법종구분", "법령구분명", "docCls"]),
        ministry=_first_str(data, ["소관부처", "소관부처명", "ministry"]),
        language=_first_str(data, ["언어", "language"]),
        articles=_extract_articles(data),
        raw=data,
    )
    return response


def fetch_law_interpretation(
    *,
    interpretation_id: Optional[str] = None,
    lm: Optional[str] = None,
    oc: Optional[str] = None,
    timeout: float = 10.0,
    base_url: str = LAW_GO_KR_DETAIL_URL,
) -> LawInterpretationDetail:
    """Fetch a legal interpretation detail from law.go.kr."""

    if not interpretation_id and not lm:
        raise LawSearchError("법령해석례 상세 조회에는 ID 또는 LM 값이 필요합니다.")

    resolved_oc = _resolve_oc(oc)
    params: Dict[str, Any] = {"OC": resolved_oc, "target": "expc", "type": "JSON"}
    if interpretation_id:
        params["ID"] = interpretation_id
    if lm:
        params["LM"] = lm

    data = _call_api(params=params, base_url=base_url, timeout=timeout)
    return LawInterpretationDetail(
        serial_no=_first_str(data, ["법령해석례일련번호", "ID", "expcId"]),
        title=_first_str(data, ["안건명", "title"]),
        case_no=_first_str(data, ["안건번호", "caseNo"]),
        interpretation_date=_format_date(_first_str(data, ["해석일자", "replyDate"])),
        interpretation_org=_first_str(data, ["해석기관명", "replyOrg"]),
        inquiry_org=_first_str(data, ["질의기관명", "inqOrg"]),
        summary=_first_str(data, ["질의요지", "summary"]),
        reply=_first_str(data, ["회답", "reply"]),
        reason=_first_str(data, ["이유", "reason"]),
        raw=data,
    )


def _resolve_oc(override: Optional[str]) -> str:
    oc = (override or os.getenv(LAW_GO_KR_OC_ENV) or "").strip()
    if not oc:
        raise LawSearchError(
            f"법령 검색 API 사용을 위해 {LAW_GO_KR_OC_ENV} 환경 변수를 설정하거나 인자로 OC 값을 전달하세요."
        )
    return oc


def _call_api(*, params: Dict[str, Any], base_url: str, timeout: float) -> Dict[str, Any]:
    query_string = parse.urlencode(params, doseq=True)
    url = f"{base_url}?{query_string}"
    redacted_params = _redact_params(params)
    redacted_url = _redact_url(base_url, redacted_params)
    logger.debug("law_go_kr_request", url=redacted_url, params=redacted_params)
    req = request.Request(url, headers={"Accept": "application/json"})
    charset: Optional[str] = None
    start_time = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status >= 400:
                raise LawSearchError(f"법령 검색 API 호출 실패 (status={status})")
            charset = resp.headers.get_content_charset() if resp.headers else None
            raw = resp.read()
            duration = time.perf_counter() - start_time
            headers_obj = resp.headers if resp.headers else None
            if headers_obj and hasattr(headers_obj, "items"):
                header_map = dict(headers_obj.items())
            else:
                header_map = {}
            logger.debug(
                "law_go_kr_response_metadata",
                url=redacted_url,
                status=status,
                charset=charset,
                content_length=len(raw),
                headers=header_map,
                duration=duration,
            )
    except error.URLError as exc:
        duration = time.perf_counter() - start_time
        logger.debug(
            "law_go_kr_request_failed",
            url=redacted_url,
            params=redacted_params,
            error=repr(exc),
            duration=duration,
        )
        raise LawSearchError(f"법령 검색 API 호출 중 오류가 발생했습니다: {exc}") from exc

    encoding = charset or "utf-8"
    try:
        text = raw.decode(encoding)
    except LookupError:
        text = raw.decode("utf-8", errors="replace")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.debug(
            "law_go_kr_response_decode_failure",
            url=redacted_url,
            encoding=encoding,
            body_preview=_clip_text(text),
        )
        raise LawSearchError(f"법령 검색 API 응답을 JSON으로 파싱하지 못했습니다: {exc}") from exc
    else:
        logger.debug(
            "law_go_kr_response_parsed",
            url=redacted_url,
            encoding=encoding,
            body_preview=_clip_text(text),
        )

    if not isinstance(data, dict):
        raise LawSearchError("법령 검색 API 응답 형식이 예상과 다릅니다 (객체가 아님)")
    return data


def _clip_text(value: str, *, limit: int = 1000) -> str:
    text = value.strip().replace("\r", " ").replace("\n", " ")
    return text if len(text) <= limit else f"{text[:limit]}…"


def _redact_params(params: Dict[str, Any], sensitive_keys: Iterable[str] = SENSITIVE_PARAM_KEYS) -> Dict[str, Any]:
    redacted = dict(params)
    for key in sensitive_keys:
        if key in redacted:
            redacted[key] = _mask_secret(redacted[key])
    return redacted


def _mask_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return MASKED_SECRET


def _redact_url(base_url: str, params: Dict[str, Any]) -> str:
    query_string = parse.urlencode(params, doseq=True)
    return f"{base_url}?{query_string}" if query_string else base_url


def _collect_entries(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if _looks_like_entry(node):
                items.append(node)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(data)
    return items


def _looks_like_entry(node: Dict[str, Any]) -> bool:
    keys = set(node.keys())
    if keys.intersection(LAW_ENTRY_KEYS):
        return True
    return bool(
        keys.intersection(INTERPRETATION_ENTRY_KEYS)
        and keys.intersection(INTERPRETATION_TITLE_KEYS)
    )


def _extract_articles(data: Dict[str, Any]) -> List[LawDetailArticle]:
    articles: List[LawDetailArticle] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if _looks_like_article(node):
                articles.append(_build_article(node))
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(data)

    uniq: Dict[str, LawDetailArticle] = {}
    ordered: List[LawDetailArticle] = []
    for article in articles:
        key = article.article_no or f"{article.title}-{len(ordered)}"
        if key in uniq:
            continue
        uniq[key] = article
        ordered.append(article)
    return ordered


def _looks_like_article(node: Dict[str, Any]) -> bool:
    keys = set(node.keys())
    return bool(keys.intersection({"조문내용", "조문번호", "조문제목"}))


def _build_article(entry: Dict[str, Any]) -> LawDetailArticle:
    article_no = _first_str(entry, ["조문번호", "조문번호문자열", "articleNo"])
    title = _first_str(entry, ["조문제목", "articleTitle"])
    content = _first_str(entry, ["조문내용", "articleContent"])
    paragraphs = _extract_paragraphs(entry)
    return LawDetailArticle(
        article_no=article_no,
        title=title,
        content=content,
        enforcement_date=_format_date(_first_str(entry, ["조문시행일자", "articleEnforceDate"])),
        amendment_type=_first_str(entry, ["조문제개정유형", "articleAmendType"]),
        paragraphs=paragraphs,
        raw=entry,
    )


def _extract_paragraphs(entry: Dict[str, Any]) -> List[LawDetailParagraph]:
    paragraphs: List[LawDetailParagraph] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            if _looks_like_paragraph(node):
                paragraphs.append(_build_paragraph(node))
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(entry)

    uniq: Dict[str, LawDetailParagraph] = {}
    ordered: List[LawDetailParagraph] = []
    for para in paragraphs:
        key = (para.number or "") + (para.text or "") + (para.clause_number or "")
        if key in uniq:
            continue
        uniq[key] = para
        ordered.append(para)
    return ordered


def _looks_like_paragraph(node: Dict[str, Any]) -> bool:
    keys = set(node.keys())
    return bool(keys.intersection({"항내용", "호내용", "항번호", "호번호"}))


def _build_paragraph(entry: Dict[str, Any]) -> LawDetailParagraph:
    return LawDetailParagraph(
        number=_first_str(entry, ["항번호", "paragraphNo"]),
        text=_first_str(entry, ["항내용", "paragraphContent", "내용"]),
        clause_number=_first_str(entry, ["호번호", "clauseNo"]),
        clause_text=_first_str(entry, ["호내용", "clauseContent"]),
        raw=entry,
    )


def _first_str(source: Any, keys: Sequence[str]) -> Optional[str]:
    value = _first_value(source, keys)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(int(value)) if isinstance(value, int) else str(value)
    if isinstance(value, str):
        return value.strip() or None
    return str(value)


def _first_int(source: Any, keys: Sequence[str]) -> Optional[int]:
    value = _first_value(source, keys)
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _first_value(source: Any, keys: Sequence[str]) -> Any:
    if isinstance(source, dict):
        for key in keys:
            if key in source and source[key] not in (None, ""):
                return source[key]
        for value in source.values():
            found = _first_value(value, keys)
            if found is not None:
                return found
    elif isinstance(source, list):
        for item in source:
            found = _first_value(item, keys)
            if found is not None:
                return found
    return None


def _format_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
    return value

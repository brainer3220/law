from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from urllib import error, parse, request

LAW_GO_KR_BASE_URL = "http://www.law.go.kr/DRF/lawSearch.do"
LAW_GO_KR_OC_ENV = "LAW_GO_KR_OC"


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
    req = request.Request(url, headers={"Accept": "application/json"})
    charset: Optional[str] = None
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if status >= 400:
                raise LawSearchError(f"법령 검색 API 호출 실패 (status={status})")
            charset = resp.headers.get_content_charset() if resp.headers else None
            raw = resp.read()
    except error.URLError as exc:
        raise LawSearchError(f"법령 검색 API 호출 중 오류가 발생했습니다: {exc}") from exc

    encoding = charset or "utf-8"
    try:
        text = raw.decode(encoding)
    except LookupError:
        text = raw.decode("utf-8", errors="replace")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LawSearchError(f"법령 검색 API 응답을 JSON으로 파싱하지 못했습니다: {exc}") from exc

    if not isinstance(data, dict):
        raise LawSearchError("법령 검색 API 응답 형식이 예상과 다릅니다 (객체가 아님)")
    return data


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
    return bool(keys.intersection({"법령명한글", "법령명", "lawId"}))


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

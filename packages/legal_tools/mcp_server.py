from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency fallback
    import structlog

    logger = structlog.get_logger(__name__)
except Exception:  # pragma: no cover - fallback to stdlib logging
    import logging

    logger = logging.getLogger(__name__)

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from packages.legal_tools.agent_graph import (
    Hit,
    USE_CASES_MD,
    tool_keyword_search,
    tool_law_go_detail,
    tool_law_go_interpretation_detail,
    tool_law_go_interpretations,
    tool_law_go_search,
)


DEFAULT_GUIDANCE = "근거가 부족하면 추가 검색을 통해 [번호] 스니펫을 확보하세요."


@dataclass
class LifespanContext:
    """Runtime context shared across MCP requests."""

    data_dir: Path


def _resolve_data_dir() -> Path:
    base = os.getenv("LAW_DATA_DIR") or "data"
    path = Path(base).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


@asynccontextmanager
async def _lifespan(_: FastMCP) -> AsyncIterator[LifespanContext]:
    data_dir = _resolve_data_dir()
    logger.info("law_mcp_startup", data_dir=str(data_dir))
    try:
        yield LifespanContext(data_dir=data_dir)
    finally:
        logger.info("law_mcp_shutdown")


mcp = FastMCP("LawTools", lifespan=_lifespan)


def _serialize_hit(hit: Hit) -> Dict[str, Any]:
    return {
        "source": hit.source,
        "path": str(hit.path),
        "doc_id": hit.doc_id,
        "title": hit.title,
        "score": hit.score,
        "snippet": hit.snippet,
        "line_no": hit.line_no,
        "page_index": hit.page_index,
        "page_total": hit.page_total,
    }


def _hits_payload(hits: List[Hit]) -> Dict[str, Any]:
    return {"hits": [_serialize_hit(hit) for hit in hits], "count": len(hits)}


@mcp.tool()
def keyword_search(
    ctx: Context[ServerSession, LifespanContext],
    *,
    query: str,
    k: int = 5,
    context_chars: int = 0,
) -> Dict[str, Any]:
    """OpenSearch 기반 키워드 검색 결과를 반환합니다."""

    hits = tool_keyword_search(
        query=query,
        k=k,
        context_chars=context_chars,
        data_dir=ctx.request_context.lifespan_context.data_dir,
    )
    return _hits_payload(hits)


@mcp.tool()
def law_statute_search(
    ctx: Context[ServerSession, LifespanContext],
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
) -> Dict[str, Any]:
    """law.go.kr 법령 검색 API를 호출합니다."""

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
    payload = _hits_payload(hits)
    payload["response"] = asdict(response)
    return payload


@mcp.tool()
def law_statute_detail(
    ctx: Context[ServerSession, LifespanContext],
    *,
    law_id: Optional[str] = None,
    mst: Optional[str] = None,
    lm: Optional[str] = None,
    ld: Optional[int] = None,
    ln: Optional[int] = None,
    jo: Optional[int] = None,
    lang: Optional[str] = None,
    oc: Optional[str] = None,
) -> Dict[str, Any]:
    """법령 본문을 law.go.kr API로 조회합니다."""

    detail, hits = tool_law_go_detail(
        law_id=law_id,
        mst=mst,
        lm=lm,
        ld=ld,
        ln=ln,
        jo=jo,
        lang=lang,
        oc=oc,
    )
    payload = _hits_payload(hits)
    payload["detail"] = asdict(detail)
    return payload


@mcp.tool()
def law_interpretation_search(
    ctx: Context[ServerSession, LifespanContext],
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
) -> Dict[str, Any]:
    """법령해석례 검색 API를 호출합니다."""

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
    payload = _hits_payload(hits)
    payload["response"] = asdict(response)
    return payload


@mcp.tool()
def law_interpretation_detail(
    ctx: Context[ServerSession, LifespanContext],
    *,
    interpretation_id: Optional[str] = None,
    lm: Optional[str] = None,
    oc: Optional[str] = None,
) -> Dict[str, Any]:
    """법령해석례 본문을 law.go.kr API로 조회합니다."""

    detail, hits = tool_law_go_interpretation_detail(
        interpretation_id=interpretation_id,
        lm=lm,
        oc=oc,
    )
    payload = _hits_payload(hits)
    payload["detail"] = asdict(detail)
    return payload


@mcp.resource("lawyer-use-cases", uri="resource://lawyer-use-cases")
def lawyer_use_cases() -> str:
    """변호사 GPT 활용 사례 마크다운을 반환합니다."""

    return USE_CASES_MD.strip()


@mcp.prompt()
def legal_summary_guidance(allow_general: bool = False) -> str:
    """LangGraph 요약 가이던스를 MCP 프롬프트로 제공합니다."""

    if allow_general:
        return "스니펫이 부족하면 최소한의 일반 법률 상식을 보충하되, 근거가 없는 문장에는 [일반지식]을 명시하세요."
    return DEFAULT_GUIDANCE


def main() -> None:
    transport = os.getenv("LAW_MCP_TRANSPORT", "streamable-http")
    logger.info("law_mcp_run", transport=transport)
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()

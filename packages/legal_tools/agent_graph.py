from __future__ import annotations

import operator
import os
import re
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TypedDict
from typing_extensions import Annotated, Literal

# LangGraph core APIs
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver


# Initialize module logger early
logger = logging.getLogger(__name__)
_LLM_BLOCKED: bool = False


def _env_true(name: str) -> bool:
    v = os.getenv(name)
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _llm_enabled() -> bool:
    if _env_true("LAW_OFFLINE"):
        return False
    if _LLM_BLOCKED:
        return False
    if not os.getenv("OPENAI_API_KEY"):
        return False
    return True


def _block_llm(err: Exception) -> None:
    global _LLM_BLOCKED
    _LLM_BLOCKED = True
    logger.warning("LLM disabled for this run (reason: %s)", err)

# ----------------------------- Simple Types -----------------------------


@dataclass
class Hit:
    """A retrieval hit with minimal fields for synthesis and citation."""

    source: Literal["keyword", "semantic", "mcp"]
    path: Path
    doc_id: str
    title: str
    score: float
    snippet: str
    line_no: Optional[int] = None


class AgentState(TypedDict):
    """LangGraph state for the legal Q&A agent.

    Accumulates queries, retrieved evidence, and an answer draft.
    """

    question: str
    # rolling attempts counter
    iters: Annotated[int, operator.add]
    # queries proposed by LLM
    queries: Annotated[List[str], operator.add]
    # queries already executed
    used_queries: Annotated[List[str], operator.add]
    # accumulated hits
    evidence: Annotated[List[Hit], operator.add]
    # running observations summary for LLM
    observations: str
    # final output
    answer: str
    citations: Annotated[List[Dict[str, Any]], operator.add]
    # termination flag set by LLM/controller
    done: bool


# ----------------------- Reference: GPT Use Cases -----------------------

# Repository note: kept as a constant for prompts/docs reuse.
USE_CASES_MD: str = """
## 변호사가 GPT를 활용하는 주요 사례

1. **문서 작성 및 초안 작성(drafting)**

   * 계약서, 합의서, 고소장, 답변서, 소장 등 법률문서의 첫 안(draft)을 작성하는 데에 시간을 단축할 수 있음. ([MyCase][1])
   * 문장 표현 개선, 전문성 있는 어조 조정 등 스타일 수정 및 교정(proofreading)에도 도움됨. ([LexisNexis][2])

2. **법률 리서치 및 사례 정리**

   * 관련 판례(case law), 법령, 논문, 규정 등을 찾아 요약해서 제공. ([purduegloballawschool.edu][3])
   * 증언 기록(transcripts), 증거 문서, 발견(discovery) 자료 등 복잡한 문서를 이해하기 쉬운 요약본으로 정리. ([MyCase][1])

3. **계약서 검토 및 위험 분석(contract review / risk assessment)**

   * 계약 조항 중 중요한 의무(obligations), 유리하거나 불리한 조항(risk) 등을 확인하고 요약함. ([juro.com][4])
   * 장황한 계약서를 핵심사항 중심으로 추출(summary / abstract)해서 빠르게 파악할 수 있게 함. ([juro.com][4])

4. **클라이언트 커뮤니케이션 / 내부 커뮤니케이션 개선**

   * 클라이언트에게 복잡한 법률용어를 쉽게 풀어서 설명하는 문서나 메일 초안 작성. ([MyCase][1])
   * 내부 보고서, 전략제안서, 사건 흐름(timeline) 정리 등 업무 공유용 자료 준비. ([purduegloballawschool.edu][3])

5. **예측 및 전략 수립**

   * 과거 판례 결과, 쟁점(issue)의 경향성을 바탕으로 승소 가능성(predictive outcome)이나 전략적 접근(어느 쟁점에 초점을 둘지 등)을 생각하는 데 참고 자료로 활용. ([MyCase][1])
   * 증거자료, 정황, 일정 등을 기반으로 일정표(timeline) 또는 사건 흐름을 시각/문서 형태로 구성. ([Business Insider][5])

6. **업무 효율화(operational tasks)**

   * 계약서 발굴(scan) 및 분류(classification) 자동화
   * 비용 청구(invoices), 법률비(Legal spend) 검토 등 반복적인 사무작업 자동화. ([arXiv][6])
   * 마케팅 자료, 웹사이트 콘텐츠, 제안서(RFP: Request for Proposal) 등 비(非)본질적인 문서 작업 시간 절약. ([MyCase][1])
"""


def get_lawyer_gpt_use_cases() -> str:
    """Return curated examples of how lawyers use GPT in practice (Markdown)."""
    return USE_CASES_MD


# -------------------------- LLM utilities -------------------------------


def _openai_chat(messages: List[Dict[str, Any]], *, model: Optional[str] = None, timeout: float = 30.0) -> str:
    """Minimal OpenAI Chat Completions client using urllib.

    Requires env `OPENAI_API_KEY`. Optional `OPENAI_BASE_URL` (default https://api.openai.com/v1)
    and `OPENAI_MODEL` if `model` is not provided.
    """
    import json as _json
    import os as _os
    import urllib.request as _url

    if not _llm_enabled():
        raise RuntimeError("LLM disabled (offline mode or missing API key)")

    api_key = _os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY to use LLM-driven agent.")
    base = _os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    mdl = model or _os.getenv("OPENAI_MODEL", "gpt-5-mini-2025-08-07")
    try:
        env_timeout = float(_os.getenv("OPENAI_TIMEOUT", "0") or 0)
        if env_timeout > 0:
            timeout = env_timeout
    except Exception:
        pass

    payload = {
        "model": mdl,
        "messages": messages,
    }
    # Some providers/models reject non-default temperatures. Honor optional env override.
    temp_env = _os.getenv("OPENAI_TEMPERATURE", "").strip()
    if temp_env:
        try:
            payload["temperature"] = float(temp_env)
        except Exception:
            # If user sets OPENAI_TEMPERATURE="default" or invalid, omit to use provider default
            pass
    req = _url.Request(
        f"{base}/chat/completions",
        data=_json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with _url.urlopen(req, timeout=timeout) as resp:  # nosec - agent assumes trusted config
            body = resp.read().decode("utf-8")
    except Exception as e:  # Surface helpful diagnostics on HTTP/connection failures
        import urllib.error as _ue
        status = None
        detail = ""
        if isinstance(e, _ue.HTTPError):
            status = getattr(e, "code", None)
            try:
                detail = e.read().decode("utf-8", errors="ignore")
            except Exception:
                detail = str(e)
        elif isinstance(e, _ue.URLError):
            detail = str(e.reason or e)
        else:
            detail = str(e)
        msg = (
            f"Chat request failed (model={mdl}, base={base}, status={status}).\n"
            "Hint: verify your provider supports this model, or set OPENAI_MODEL/OPENAI_BASE_URL.\n"
            f"Detail: {detail[:400]}"
        )
        raise RuntimeError(msg) from e
    data = _json.loads(body)
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"Unexpected OpenAI response: {body[:400]}")


def _llm_decide(question: str, observations: str, iters: int, max_iters: int) -> Dict[str, Any]:
    """Ask the LLM what to do next: `search` with a query or `final` with an answer.

    Returns a dict like {"action": "search", "query": "..."} or {"action": "final", "answer": "..."}.
    """
    sys = (
        "당신은 법률 RAG 에이전트의 컨트롤러입니다. 모든 단계에서 다음 중 하나를 선택하세요:\n"
        "- search: 더 구체적인 검색 질의를 제안합니다.\n"
        "- final: 축약된 답변을 작성합니다. 각 문장에 근거(문서/판례/문장 스니펫)를 포함하세요.\n"
        "검색 지침: 긴 문장 대신 핵심 단어 단위(1~3 단어)로 질의를 구성하세요.\n"
        "필요하면 서로 다른 조합으로 여러 번 검색하고, 이미 시도한 질의는 반복하지 마세요.\n"
        f"현재 반복: {iters}/{max_iters}. 반복 한도에 도달하면 반드시 final을 출력하세요.\n\n"
        "[내부 참고자료 — 출력 금지]\n"
        "아래 사례는 에이전트의 목적/역할을 상기시키기 위한 것입니다. 의사결정에만 참고하고, 그대로 답변에 포함하지 마세요.\n"
        + get_lawyer_gpt_use_cases()
    )
    user = (
        f"질문: {question}\n\n"
        "지금까지 관찰된 스니펫(최신이 하단):\n"
        f"{observations or '(없음)'}\n\n"
        "JSON으로만 답하세요. 예시:\n"
        "{\"action\":\"search\",\"query\":\"주 40시간제 대법원 판결 판례\"}\n"
        "또는\n"
        "{\"action\":\"final\",\"answer\":\"...\"}"
    )
    logger.info(
        "decide: iters=%s/%s, obs_chars=%s", iters, max_iters, len(observations or "")
    )
    if not _llm_enabled():
        logger.info("decide: LLM disabled (offline) -> final")
        return {"action": "final", "answer": ""}
    try:
        out = _openai_chat([
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ])
    except Exception as e:
        _block_llm(e)
        logger.info("decide: falling back to final after LLM error")
        return {"action": "final", "answer": ""}
    # Best-effort JSON extract
    import json as _json
    import re as _re

    m = _re.search(r"\{[\s\S]*\}", out)
    if not m:
        logger.info("decide: no JSON detected; defaulting to final")
        return {"action": "final", "answer": out.strip()[:2000]}
    try:
        decision = _json.loads(m.group(0))
        action = str(decision.get("action", "final")).lower()
        if action == "search":
            logger.info("decide: action=search query=%s", (decision.get("query") or "").strip())
        else:
            logger.info("decide: action=final (LLM)")
        return decision
    except Exception:
        logger.info("decide: JSON parse failed; defaulting to final")
        return {"action": "final", "answer": out.strip()[:2000]}


def _llm_finalize(question: str, observations: str, *, allow_general: bool = False) -> str:
    """Ask the LLM to produce a concise, grounded answer using observations only.

    Output should contain brief sentences with inline numbered references mapping to the
    provided snippets (e.g., [1], [2]). No speculative claims.
    """
    if allow_general:
        sys = (
            "당신은 법률 리서치 요약가입니다. \n"
            "가능하면 관측된 스니펫을 우선 근거로 삼아 답변하세요.\n"
            "스니펫이 부족/없으면 일반적으로 알려진 법리·개요를 간략히 보완할 수 있습니다.\n"
            "이때 스니펫에 직접 근거하지 않은 문장에는 [일반지식] 표시를 붙이세요.\n"
            "법률 자문은 금지하며, 사실 요약과 출처 제시에 집중하세요.\n\n"
            "[내부 참고자료 — 출력 금지]\n"
            "아래 사례는 에이전트의 목적/역할을 상기시키기 위한 것입니다. 구성/톤만 참고하고, 그대로 답변에 포함하지 마세요.\n"
            + get_lawyer_gpt_use_cases()
            + "\n"
            "출력 형식: 사건 정보(가능하면), 요약, 법원 판단(핵심) 인용, 결론, 출처 및 메타데이터."
        )
    else:
        sys = (
            "당신은 법률 리서치 요약가입니다. 관측된 스니펫만 근거로 간결한 답변을 작성하세요.\n"
            "법률 자문은 금지하며, 사실 요약과 출처 제시에 집중하세요.\n\n"
            "[내부 참고자료 — 출력 금지]\n"
            "아래 사례는 에이전트의 목적/역할을 상기시키기 위한 것입니다. 구성/톤만 참고하고, 그대로 답변에 포함하지 마세요.\n"
            + get_lawyer_gpt_use_cases()
            + "\n"
            "출력 형식: 사건 정보(가능하면), 요약, 법원 판단(핵심) 인용, 결론, 출처 및 메타데이터."
        )
    user = (
        f"질문: {question}\n\n"
        "관측된 스니펫(번호는 그대로 사용):\n"
        f"{observations or '(없음)'}\n\n"
        "아래 지침을 지켜 한국어로 구조화된 마크다운을 작성하세요.\n"
        "- 사건 정보: 가능하면 법원명/사건번호를 간단히 정리 (없으면 생략)\n"
        "- 요약: 간결하게 핵심만\n"
        "- 법원 판단(핵심): 관측 스니펫을 1~2문장 인용(\"\"로 표시)하며 [번호]로 출처 표기\n"
        "- 결론: 요약 재진술 (스니펫 근거가 없는 문장은 [일반지식] 표시)\n"
        "- 출처 및 메타데이터: [번호]만 나열 (경로/파일명은 생략)\n"
    )
    logger.info("finalize: composing answer (allow_general=%s)", allow_general)
    if not _llm_enabled():
        logger.info("finalize: LLM disabled (offline) -> offline summary")
        return _offline_summary(question, observations)
    try:
        return _openai_chat([
            {"role": "system", "content": sys},
            {"role": "user", "content": user},
        ])
    except Exception as e:
        _block_llm(e)
        logger.info("finalize: offline deterministic summary after LLM error")
        return _offline_summary(question, observations)


def _offline_summary(question: str, observations: str) -> str:
    """Deterministic offline fallback when LLM is unavailable.

    Builds a concise markdown using available observations only.
    """
    obs = (observations or "").strip()
    if not obs:
        return (
            "# 사건 정보\n(관측된 스니펫 없음 — 사건 정보 제공 불가)\n\n"
            "# 요약\n"
            "관측된 스니펫이 제공되지 않아 근거 기반 요약을 생성할 수 없습니다. 관련 스니펫을 확보하거나 Postgres 검색 구성을 확인하세요.\n\n"
            "# 법원 판단(핵심)\n"
            "인용할 스니펫이 없어 법원 판단을 제시할 수 없습니다.\n\n"
            "# 결론\n"
            "증거 스니펫이 필요합니다. 스니펫을 제공하거나 데이터 인덱스를 점검하세요. [일반지식]\n\n"
            "# 출처 및 메타데이터\n(번호 없음)"
        )
    # Use up to first 2 observation lines as quotes
    lines = [ln.strip() for ln in obs.splitlines() if ln.strip()]
    quotes = []
    refs = []
    for ln in lines:
        if ln.startswith("[") and "]" in ln:
            try:
                num = int(ln[1: ln.index("]")])
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


def _seed_queries(question: str) -> List[str]:
    """Deterministic first-round queries to avoid empty observations.

    - Always include the question itself and `판례` 확장.
    - Add domain synonyms when certain keywords are present (e.g., 타임오프 for 근로시간 면제).
    """
    q = question.strip()
    out: List[str] = []
    if q:
        out.append(q)
        if "판례" not in q:
            out.append(f"{q} 판례")
    lower = q.replace(" ", "")
    # Labor time-off synonyms
    if any(k in lower for k in ["근로시간면제", "근로시간", "면제업무", "타임오프"]):
        out.extend(["근로시간면제", "타임오프", "노조 전임자 근로시간면제"])
    # Generic court markers to nudge retrieval toward cases
    out.extend([f"{q} 대법원", f"{q} 판결"] if q else [])
    # De-duplicate and cap
    seen = set()
    uniq: List[str] = []
    for s in out:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            uniq.append(s)
        if len(uniq) >= 5:
            break
    logger.info("seed_queries: %s", ", ".join(uniq))
    return uniq


# -------------------------- Retrieval utils ----------------------------


def _keyword_search(query: str, limit: int, data_dir: Path, *, context_chars: int = 0) -> List[Hit]:
    """Use Postgres pg_search (BM25) or fallback FTS via packages.legal_tools.pg_search."""
    try:
        from packages.legal_tools.pg_search import search_bm25
    except Exception as e:
        raise RuntimeError("Postgres search backend is required. Install psycopg and set SUPABASE_DB_URL/PG_DSN.") from e

    logger.info("search[keyword]: query=%s limit=%s", query, limit)
    rows = search_bm25(query, limit=max(5, limit))
    hits: List[Hit] = []
    for r in rows:
        snippet = r.snippet or ""
        if context_chars and r.body:
            ctx = (r.body or "")
            if context_chars > 0 and len(ctx) > context_chars:
                ctx = ctx[: context_chars - 3] + "..."
            # Combine highlighted snippet and raw body context
            snippet = (snippet + "\n" + ctx).strip()
        # Cap overly long snippet for safety in prompts
        if len(snippet) > 1200:
            snippet = snippet[:1197] + "..."
        try:
            p = Path(r.path) if r.path else Path("")
        except Exception:
            p = Path("")
        hits.append(
            Hit(
                source="keyword",
                path=p,
                doc_id=r.doc_id,
                title=r.title,
                score=r.score,
                snippet=snippet,
                line_no=None,
            )
        )
    logger.info("search[keyword]: hits=%s (pre-dedupe)", len(hits))
    return hits


# (semantic/vector search removed)


def _is_case_like(hit: Hit) -> bool:
    """Heuristically judge if a hit looks like case law (판례)."""
    text = " ".join([hit.title, hit.snippet])
    # Case markers: court terms or docket-like IDs
    if re.search(r"대법원|고등법원|판결|판례|주문|이유", text):
        return True
    if re.search(r"\b\d{4}[가-힣]{1}\d{3,6}\b", text):
        return True
    return False


def _dedupe_hits(hits: Iterable[Hit]) -> List[Hit]:
    seen: set = set()
    out: List[Hit] = []
    for h in hits:
        key = (h.doc_id, h.path, h.snippet[:80])
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


# ----------------------------- Nodes -----------------------------------


def decide(state: AgentState, *, max_iters: int, allow_general: bool = False) -> Dict[str, Any]:
    """Delegate to the LLM for next action: search or final."""
    q = state.get("question", "")
    obs = state.get("observations", "")
    iters = int(state.get("iters", 0))
    # Force a deterministic first search if nothing observed yet
    if iters == 0 and not obs:
        seeds = _seed_queries(q)
        if seeds:
            logger.info("decide: bootstrap seeds -> %s", ", ".join(seeds[:3]))
            return {"queries": seeds[:3], "iters": 1, "done": False}
    decision = _llm_decide(q, obs, iters, max_iters)
    action = str(decision.get("action", "final")).lower()
    will_reach_limit = (iters + 1) >= max_iters
    if action == "search" and not will_reach_limit:
        query = str(decision.get("query", "")).strip() or q
        logger.info("decide: continue with query=%s (iters=%s)", query, iters + 1)
        return {"queries": [query], "iters": 1, "done": False}
    # Finalize: either LLM asked to finalize, or we hit the limit — ask LLM for final
    ans = str(decision.get("answer", "")).strip()
    if not ans:
        ans = _llm_finalize(q, obs, allow_general=allow_general).strip()
    logger.info("decide: finalize (iters=%s)", iters)
    return {"answer": ans or "(LLM 응답이 비어있습니다)", "queries": [], "done": True}


def retrieve(state: AgentState, *, data_dir: Path, k: int, context_chars: int = 0) -> Dict[str, Any]:
    """Run keyword + semantic retrieval for new queries and accumulate hits."""
    new_qs = state.get("queries", [])
    used = set(state.get("used_queries", []))
    evidence: List[Hit] = []
    logger.info("retrieve: %s new queries (k=%s, context_chars=%s)", len(new_qs), k, context_chars)
    for q in new_qs:
        if q in used:
            continue
        # MCP tool prefix handling
        if q.lower().startswith("mcp:"):
            try:
                kind_rest = q.split(":", 2)[1:]
                kind = (kind_rest[0] if kind_rest else "").strip().lower()
                rest = kind_rest[1] if len(kind_rest) > 1 else ""
                from urllib.parse import urlparse, parse_qs
                title = ""
                snippet = ""
                if kind == "context7":
                    lib, _, qs = rest.partition("?")
                    params = parse_qs(qs)
                    topic = (params.get("topic", [""])[0] or None)
                    try:
                        tokens = int(params.get("tokens", ["4000"])[0])
                    except Exception:
                        tokens = 4000
                    try:
                        from packages.legal_tools.mcp_client import context7_docs  # type: ignore
                        out = context7_docs(lib, topic=topic, tokens=min(10000, max(1000, tokens)))
                        title = f"MCP Context7: {lib} ({topic or 'docs'})"
                        snippet = (out or "").strip()
                    except Exception as e:  # MCP unavailable or failed
                        title = f"MCP Context7: {lib}"
                        snippet = f"[MCP] Context7 failed: {e}"
                elif kind == "astgrep":
                    patt, _, qs = rest.partition("?")
                    params = parse_qs(qs)
                    language = (params.get("language", [""])[0] or None)
                    try:
                        max_results = int(params.get("max", params.get("max_results", ["50"]))[0])
                    except Exception:
                        max_results = 50
                    project = (params.get("project", [""])[0] or ".")
                    try:
                        from packages.legal_tools.mcp_client import ast_grep_find  # type: ignore
                        out = ast_grep_find(patt, project_dir=project, language=language, max_results=max_results)
                        title = f"MCP ast-grep: {patt}"
                        snippet = (out or "").strip()
                    except Exception as e:
                        title = f"MCP ast-grep: {patt}"
                        snippet = f"[MCP] ast-grep failed: {e}"
                else:
                    title = f"MCP: {q}"
                    snippet = "[MCP] Unknown MCP kind. Use mcp:context7:... or mcp:astgrep:..."
                # Truncate overly long snippet
                if len(snippet) > 1200:
                    snippet = snippet[:1197] + "..."
                evidence.append(
                    Hit(
                        source="mcp",
                        path=Path(""),
                        doc_id=f"mcp:{kind}",
                        title=title,
                        score=0.0,
                        snippet=snippet,
                        line_no=None,
                    )
                )
                logger.info("retrieve: mcp %s -> appended note (len=%s)", kind, len(snippet))
            except Exception:
                logger.exception("retrieve: MCP handling failed for %s", q)
            continue
        # keyword search (default)
        try:
            q_hits = _keyword_search(q, limit=max(5, k), data_dir=data_dir, context_chars=context_chars)
            evidence.extend(q_hits)
            logger.info("retrieve: query=%s -> %s hits", q, len(q_hits))
        except Exception:
            logger.exception("retrieve: keyword search failed for query=%s", q)
    # Merge and de-dup; prefer case-like first
    evidence = sorted(evidence, key=lambda h: (not _is_case_like(h), -h.score))
    evidence = _dedupe_hits(evidence)[: max(10, k * 2)]
    # Build observation summary for the LLM
    lines: List[str] = []
    for i, h in enumerate(evidence[:k], start=1):
        pin = f"L{h.line_no}" if h.line_no else "snippet"
        lines.append(f"[{i}] {h.title} ({h.doc_id}) {pin}: {h.snippet}")
    obs = (state.get("observations") or "")
    obs = (obs + "\n" if obs else "") + ("\n".join(lines))
    # Basic citations mirror
    citations: List[Dict[str, Any]] = []
    for i, h in enumerate(evidence[:k], start=1):
        citations.append(
            {
                "rank": i,
                "doc_id": h.doc_id,
                "title": h.title,
                "path": str(h.path) if h.path else "",
                "pin_cite": (f"L{h.line_no}" if h.line_no else "snippet"),
                "snippet": h.snippet,
                "source": h.source,
            }
        )
    logger.info("retrieve: retained %s evidence; summarizing top %s", len(evidence), min(k, len(evidence)))
    return {
        "evidence": evidence,
        "used_queries": list(used.union(new_qs)),
        "observations": obs,
        "citations": citations,
    }


def finish_if_ready(state: AgentState) -> Dict[str, Any]:
    """No-op node used when LLM already produced final answer in `decide`."""
    return {}


# ----------------------------- Graph build ------------------------------


def build_legal_ask_graph(*, data_dir: Path, top_k: int = 5, max_iters: int = 3, allow_general: bool = False, context_chars: int = 0):
    """LLM-driven loop: decide -> (search) -> decide ... -> final.

    - decide: LLM outputs either {action: search, query} or {action: final, answer}.
    - search: runs keyword search, appends observations and citations.
    """

    def decide_node(state: AgentState):
        return decide(state, max_iters=max_iters, allow_general=allow_general)

    def search_node(state: AgentState):
        return retrieve(state, data_dir=data_dir, k=top_k, context_chars=context_chars)

    def route_after_decide(state: AgentState) -> Literal["search", "finish"]:
        if state.get("done"):
            return "finish"
        if state.get("queries"):
            return "search"
        return "finish"

    workflow = StateGraph(AgentState)
    workflow.add_node("decide", decide_node)
    workflow.add_node("search", search_node)
    workflow.add_node("finish", finish_if_ready)

    workflow.add_edge(START, "decide")
    workflow.add_conditional_edges("decide", route_after_decide, {"search": "search", "finish": "finish"})
    workflow.add_edge("search", "decide")
    workflow.add_edge("finish", END)

    memory = InMemorySaver()
    logger.info(
        "graph: compiled (top_k=%s, max_iters=%s, allow_general=%s, context_chars=%s)",
        top_k,
        max_iters,
        allow_general,
        context_chars,
    )
    return workflow.compile(checkpointer=memory)


def run_ask(question: str, *, data_dir: Path, top_k: int = 5, max_iters: int = 3, allow_general: bool = False, context_chars: int = 0) -> Dict[str, Any]:
    """Convenience entry: run the LangGraph and return final state."""
    graph = build_legal_ask_graph(
        data_dir=data_dir,
        top_k=top_k,
        max_iters=max_iters,
        allow_general=allow_general,
        context_chars=context_chars,
    )
    thread_id = os.urandom(6).hex()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": max(10, max_iters * 5)}
    # Provide initial empty state
    init: AgentState = {
        "question": question,
        "iters": 0,
        "queries": [],
        "used_queries": [],
        "evidence": [],
        "observations": "",
        "answer": "",
        "citations": [],
        "done": False,
    }
    logger.info(
        "run_ask: start thread_id=%s question=%s", thread_id, (question or "").strip()[:80]
    )
    final = graph.invoke(init, config)
    logger.info(
        "run_ask: done thread_id=%s keys=%s", thread_id, ",".join(sorted(final.keys()))
    )
    return final

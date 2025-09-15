from __future__ import annotations

import operator
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TypedDict
from typing_extensions import Annotated, Literal

# LangGraph core APIs
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver


# ----------------------------- Simple Types -----------------------------


@dataclass
class Hit:
    """A retrieval hit with minimal fields for synthesis and citation."""

    source: Literal["keyword", "semantic"]
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


# -------------------------- LLM utilities -------------------------------


def _openai_chat(messages: List[Dict[str, Any]], *, model: Optional[str] = None, timeout: float = 30.0) -> str:
    """Minimal OpenAI Chat Completions client using urllib.

    Requires env `OPENAI_API_KEY`. Optional `OPENAI_BASE_URL` (default https://api.openai.com/v1)
    and `OPENAI_MODEL` if `model` is not provided.
    """
    import json as _json
    import os as _os
    import urllib.request as _url

    api_key = _os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY to use LLM-driven agent.")
    base = _os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    mdl = model or _os.getenv("OPENAI_MODEL", "gpt-5-mini-2025-08-07")

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
        f"현재 반복: {iters}/{max_iters}. 반복 한도에 도달하면 반드시 final을 출력하세요."
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
    out = _openai_chat([
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ])
    # Best-effort JSON extract
    import json as _json
    import re as _re

    m = _re.search(r"\{[\s\S]*\}", out)
    if not m:
        return {"action": "final", "answer": out.strip()[:2000]}
    try:
        return _json.loads(m.group(0))
    except Exception:
        return {"action": "final", "answer": out.strip()[:2000]}


def _llm_finalize(question: str, observations: str) -> str:
    """Ask the LLM to produce a concise, grounded answer using observations only.

    Output should contain brief sentences with inline numbered references mapping to the
    provided snippets (e.g., [1], [2]). No speculative claims.
    """
    sys = (
        "당신은 법률 리서치 요약가입니다. 관측된 스니펫만 근거로 간결한 답변을 작성하세요.\n"
        "법률 자문을 하지 말고, 사실 요약과 출처 제시에 집중하세요.\n"
        "각 주장에는 [번호] 형태의 근거 지시를 포함하세요."
    )
    user = (
        f"질문: {question}\n\n"
        "관측된 스니펫(번호는 그대로 사용):\n"
        f"{observations or '(없음)'}\n\n"
        "간결한 답변을 한국어로 작성하세요."
    )
    return _openai_chat([
        {"role": "system", "content": sys},
        {"role": "user", "content": user},
    ])


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
    return uniq


# -------------------------- Retrieval utils ----------------------------


def _keyword_search(query: str, limit: int, data_dir: Path) -> List[Hit]:
    """Use Postgres pg_search (BM25) or fallback FTS via packages.legal_tools.pg_search."""
    try:
        from packages.legal_tools.pg_search import search_bm25
    except Exception as e:
        raise RuntimeError("Postgres search backend is required. Install psycopg and set SUPABASE_DB_URL/PG_DSN.") from e

    rows = search_bm25(query, limit=max(5, limit))
    hits: List[Hit] = []
    for r in rows:
        snippet = r.snippet if len(r.snippet) <= 200 else r.snippet[:197] + "..."
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


def decide(state: AgentState, *, max_iters: int) -> Dict[str, Any]:
    """Delegate to the LLM for next action: search or final."""
    q = state.get("question", "")
    obs = state.get("observations", "")
    iters = int(state.get("iters", 0))
    # Force a deterministic first search if nothing observed yet
    if iters == 0 and not obs:
        seeds = _seed_queries(q)
        if seeds:
            return {"queries": seeds[:3], "iters": 1, "done": False}
    decision = _llm_decide(q, obs, iters, max_iters)
    action = str(decision.get("action", "final")).lower()
    will_reach_limit = (iters + 1) >= max_iters
    if action == "search" and not will_reach_limit:
        query = str(decision.get("query", "")).strip() or q
        return {"queries": [query], "iters": 1, "done": False}
    # Finalize: either LLM asked to finalize, or we hit the limit — ask LLM for final
    ans = str(decision.get("answer", "")).strip()
    if not ans:
        ans = _llm_finalize(q, obs).strip()
    return {"answer": ans or "(LLM 응답이 비어있습니다)", "queries": [], "done": True}


def retrieve(state: AgentState, *, data_dir: Path, k: int) -> Dict[str, Any]:
    """Run keyword + semantic retrieval for new queries and accumulate hits."""
    new_qs = state.get("queries", [])
    used = set(state.get("used_queries", []))
    evidence: List[Hit] = []
    for q in new_qs:
        if q in used:
            continue
        # keyword-only
        try:
            evidence.extend(_keyword_search(q, limit=max(5, k), data_dir=data_dir))
        except Exception:
            pass
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


def build_legal_ask_graph(*, data_dir: Path, top_k: int = 5, max_iters: int = 3):
    """LLM-driven loop: decide -> (search) -> decide ... -> final.

    - decide: LLM outputs either {action: search, query} or {action: final, answer}.
    - search: runs keyword search, appends observations and citations.
    """

    def decide_node(state: AgentState):
        return decide(state, max_iters=max_iters)

    def search_node(state: AgentState):
        return retrieve(state, data_dir=data_dir, k=top_k)

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
    return workflow.compile(checkpointer=memory)


def run_ask(question: str, *, data_dir: Path, top_k: int = 5, max_iters: int = 3) -> Dict[str, Any]:
    """Convenience entry: run the LangGraph and return final state."""
    graph = build_legal_ask_graph(data_dir=data_dir, top_k=top_k, max_iters=max_iters)
    config = {"configurable": {"thread_id": os.urandom(6).hex()}, "recursion_limit": max(10, max_iters * 5)}
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
    final = graph.invoke(init, config)
    return final

"""Legal research memo generation (BRA-23).

Turns a natural-language legal question into a structured Korean research
memo (리서치 메모) with the sections lawyers expect:

    사실관계 (facts) -> 쟁점 (issues) -> 법리 (authorities) -> 결론 (conclusion)
    -> 리스크 (risks / open questions)

Retrieval is grounded through the existing ``run_ask`` agent so every memo
section can cite the same corpus the Q&A flow uses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMO_SECTIONS: List[str] = ["사실관계", "쟁점", "법리", "결론", "리스크"]

_SECTION_PROMPTS: Dict[str, str] = {
    "사실관계": (
        "다음 법률 질문에서 확인 가능한 사실관계만 정리해줘. 추측은 배제하고, "
        "질문에 없는 사실은 '확인 필요'로 표시해줘.\n\n질문: {question}"
    ),
    "쟁점": (
        "다음 법률 질문의 핵심 법적 쟁점을 번호 목록으로 추출해줘. 각 쟁점은 "
        "한 문장으로 작성해줘.\n\n질문: {question}"
    ),
    "법리": (
        "다음 법률 질문의 각 쟁점에 적용될 법령·판례·행정해석을 조사해줘. "
        "근거의 정확한 명칭과 조문/사건번호를 인용하고, 확인되지 않는 인용은 "
        "만들지 마.\n\n질문: {question}"
    ),
    "결론": (
        "지금까지의 사실관계·쟁점·법리를 바탕으로 결론을 요약해줘. 단정이 "
        "어려운 부분은 조건부로 표기해줘.\n\n질문: {question}"
    ),
    "리스크": (
        "이 사안의 실무 리스크와 추가 확인이 필요한 사항을 정리해줘. 반대 "
        "해석 가능성, 시효·기간, 증거 문제를 포함해줘.\n\n질문: {question}"
    ),
}


@dataclass
class ResearchMemo:
    """Structured research memo."""

    question: str
    sections: Dict[str, str] = field(default_factory=dict)
    citations: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = ["# 리서치 메모", "", f"**질의**: {self.question}", ""]
        for section in MEMO_SECTIONS:
            body = self.sections.get(section, "").strip() or "(내용 없음)"
            lines.append(f"## {section}")
            lines.append("")
            lines.append(body)
            lines.append("")
        if self.citations:
            lines.append("## 인용 근거")
            lines.append("")
            for cite in self.citations:
                lines.append(f"- {cite}")
            lines.append("")
        return "\n".join(lines)


def _extract_citations(result: Dict[str, Any]) -> List[str]:
    citations: List[str] = []
    for key in ("citations", "sources", "evidence"):
        items = result.get(key)
        if not items:
            continue
        for item in items:
            if isinstance(item, str):
                citations.append(item)
            elif isinstance(item, dict):
                label = item.get("title") or item.get("doc_id") or item.get("id")
                if label:
                    citations.append(str(label))
    return citations


def build_research_memo(
    question: str,
    *,
    data_dir: Path,
    top_k: int = 5,
    max_iters: int = 3,
    sections: Optional[List[str]] = None,
    runner: Optional[Any] = None,
) -> ResearchMemo:
    """Build a structured research memo for *question*.

    ``runner`` defaults to ``agent_graph.run_ask``; tests inject a stub.
    """

    if runner is None:
        from law_shared.legal_tools.agent_graph import run_ask as runner

    memo = ResearchMemo(question=question)
    wanted = sections or MEMO_SECTIONS
    for section in wanted:
        template = _SECTION_PROMPTS.get(section)
        if template is None:
            continue
        result = runner(
            template.format(question=question),
            data_dir=data_dir,
            top_k=top_k,
            max_iters=max_iters,
        )
        answer = ""
        if isinstance(result, dict):
            answer = str(result.get("answer") or result.get("output") or "")
            memo.citations.extend(_extract_citations(result))
        else:
            answer = str(result)
        memo.sections[section] = answer.strip()

    # de-duplicate citations while preserving order
    seen = set()
    memo.citations = [c for c in memo.citations if not (c in seen or seen.add(c))]
    return memo

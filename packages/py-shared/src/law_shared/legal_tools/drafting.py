"""Legal document drafting support (BRA-24, BRA-8).

Generates first drafts (초안) of common Korean litigation documents and
supports revision instructions (파트너 피드백 반영). Draft structure is
deterministic (templates below); section bodies are grounded through the
``run_ask`` agent so citations come from the same corpus as Q&A.

Supported document types:
    소장, 답변서, 준비서면, 가처분신청서, 가압류신청서, 법률의견서, 보정서
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DOCUMENT_TYPES: List[str] = [
    "소장",
    "답변서",
    "준비서면",
    "가처분신청서",
    "가압류신청서",
    "법률의견서",
    "보정서",
]

# Deterministic section skeletons per document type.
_TEMPLATES: Dict[str, List[str]] = {
    "소장": ["당사자 표시", "청구취지", "청구원인", "입증방법", "첨부서류", "말미"],
    "답변서": ["당사자 표시", "답변의 요지", "청구원인에 대한 답변", "항변", "입증방법", "말미"],
    "준비서면": ["사건 표시", "주장 정리", "법리", "증거 설명", "말미"],
    "가처분신청서": ["당사자 표시", "신청취지", "피보전권리", "보전의 필요성", "입증방법", "말미"],
    "가압류신청서": ["당사자 표시", "신청취지", "피보전채권", "보전의 필요성", "입증방법", "말미"],
    "법률의견서": ["의뢰의 배경", "질의 요지", "검토", "결론", "리스크 및 유의사항"],
    "보정서": ["사건 표시", "보정 사유", "보정 내용", "말미"],
}

_SECTION_INSTRUCTION = (
    "다음은 {doc_type}의 '{section}' 섹션입니다. 사건 개요와 참고 지시를 "
    "반영해 한국어 실무 서면 문체로 초안을 작성해줘. 근거 법령·판례를 인용할 "
    "때는 확인된 명칭만 사용하고, 지어내지 마.\n\n사건 개요: {overview}\n"
    "참고 지시: {instructions}"
)


@dataclass
class DocumentDraft:
    """A drafted legal document."""

    doc_type: str
    overview: str
    sections: Dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [f"# {self.doc_type} (초안)", ""]
        for section in _TEMPLATES.get(self.doc_type, []):
            body = self.sections.get(section, "").strip() or "(작성 필요)"
            lines.append(f"## {section}")
            lines.append("")
            lines.append(body)
            lines.append("")
        return "\n".join(lines)


def draft_document(
    doc_type: str,
    overview: str,
    *,
    instructions: str = "",
    data_dir: Path,
    top_k: int = 5,
    max_iters: int = 3,
    runner: Optional[Any] = None,
) -> DocumentDraft:
    """Draft *doc_type* for the matter described by *overview*."""

    if doc_type not in _TEMPLATES:
        raise ValueError(
            f"지원하지 않는 문서 유형입니다: {doc_type} (지원: {', '.join(DOCUMENT_TYPES)})"
        )

    if runner is None:
        from law_shared.legal_tools.agent_graph import run_ask as runner

    draft = DocumentDraft(doc_type=doc_type, overview=overview)
    for section in _TEMPLATES[doc_type]:
        prompt = _SECTION_INSTRUCTION.format(
            doc_type=doc_type,
            section=section,
            overview=overview,
            instructions=instructions or "없음",
        )
        result = runner(
            prompt,
            data_dir=data_dir,
            top_k=top_k,
            max_iters=max_iters,
        )
        answer = ""
        if isinstance(result, dict):
            answer = str(result.get("answer") or result.get("output") or "")
        else:
            answer = str(result)
        draft.sections[section] = answer.strip()
    return draft


_REVISION_INSTRUCTION = (
    "다음은 {doc_type} 초안입니다. 아래 피드백을 반영해 수정한 전문을 "
    "반환해줘. 서면의 구조와 문체는 유지하고, 피드백과 무관한 부분은 바꾸지 "
    "마.\n\n[초안]\n{draft}\n\n[피드백]\n{feedback}"
)


def revise_document(
    draft: DocumentDraft,
    feedback: str,
    *,
    data_dir: Path,
    top_k: int = 5,
    max_iters: int = 3,
    runner: Optional[Any] = None,
) -> DocumentDraft:
    """Apply partner feedback to an existing draft."""

    if runner is None:
        from law_shared.legal_tools.agent_graph import run_ask as runner

    prompt = _REVISION_INSTRUCTION.format(
        doc_type=draft.doc_type,
        draft=draft.to_markdown(),
        feedback=feedback,
    )
    result = runner(
        prompt,
        data_dir=data_dir,
        top_k=top_k,
        max_iters=max_iters,
    )
    answer = ""
    if isinstance(result, dict):
        answer = str(result.get("answer") or result.get("output") or "")
    else:
        answer = str(result)

    revised = DocumentDraft(doc_type=draft.doc_type, overview=draft.overview)
    body = answer.strip() or draft.to_markdown()
    revised.sections = {"전문": body}
    return revised

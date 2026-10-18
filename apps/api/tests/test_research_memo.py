"""Unit tests for the research memo builder (BRA-23)."""

from __future__ import annotations

from pathlib import Path

from law_shared.legal_tools.research_memo import MEMO_SECTIONS, build_research_memo


def _stub_runner(question, *, data_dir, top_k, max_iters):
    return {
        "answer": f"[stub] {question[:30]}",
        "citations": ["민법 제750조", "대법원 2020다12345"],
    }


def test_build_research_memo_sections(tmp_path: Path) -> None:
    memo = build_research_memo(
        "근로시간 면제업무 관련 판례 조사",
        data_dir=tmp_path,
        runner=_stub_runner,
    )
    assert list(memo.sections.keys()) == MEMO_SECTIONS
    for section in MEMO_SECTIONS:
        assert memo.sections[section].startswith("[stub]")
    assert memo.citations == ["민법 제750조", "대법원 2020다12345"]


def test_memo_markdown_contains_all_sections(tmp_path: Path) -> None:
    memo = build_research_memo(
        "가산금 면제 요건",
        data_dir=tmp_path,
        runner=_stub_runner,
    )
    md = memo.to_markdown()
    for section in MEMO_SECTIONS:
        assert f"## {section}" in md
    assert "## 인용 근거" in md


def test_citations_deduplicated(tmp_path: Path) -> None:
    memo = build_research_memo(
        "중복 인용 테스트",
        data_dir=tmp_path,
        runner=_stub_runner,
    )
    assert memo.citations.count("민법 제750조") == 1

"""Unit tests for the legal drafting module (BRA-24)."""

from __future__ import annotations

from pathlib import Path

import pytest

from law_shared.legal_tools.drafting import (
    DOCUMENT_TYPES,
    _TEMPLATES,
    draft_document,
    revise_document,
)


def _stub_runner(question, *, data_dir, top_k, max_iters):
    return {"answer": f"[stub draft] {question[:40]}", "citations": []}


@pytest.mark.parametrize("doc_type", DOCUMENT_TYPES)
def test_draft_document_all_types(tmp_path: Path, doc_type: str) -> None:
    draft = draft_document(
        doc_type,
        "테스트 사건 개요",
        data_dir=tmp_path,
        runner=_stub_runner,
    )
    expected_sections = _TEMPLATES[doc_type]
    assert list(draft.sections.keys()) == expected_sections
    md = draft.to_markdown()
    for section in expected_sections:
        assert f"## {section}" in md


def test_draft_document_rejects_unknown_type(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        draft_document("행정심판청구서", "개요", data_dir=tmp_path, runner=_stub_runner)


def test_revise_document_applies_feedback(tmp_path: Path) -> None:
    draft = draft_document("준비서면", "개요", data_dir=tmp_path, runner=_stub_runner)
    revised = revise_document(
        draft,
        "청구취지를 더 구체적으로",
        data_dir=tmp_path,
        runner=_stub_runner,
    )
    assert revised.doc_type == "준비서면"
    assert "전문" in revised.sections

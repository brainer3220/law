from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from law_shared.legal_tools.file_store import (
    build_doc_id,
    ensure_layout,
    normalized_root,
    raw_root,
    read_json,
    sanitize_token,
    write_json,
)


def normalize_documents(
    *,
    data_dir: Path,
    source_type: Optional[str] = None,
) -> Dict[str, int]:
    ensure_layout(data_dir)
    raw_base = raw_root(data_dir)
    files = list(_iter_raw_files(raw_base=raw_base, source_type=source_type))
    created = 0
    for path in files:
        payload = read_json(path)
        doc = _normalize_one(payload=payload, raw_path=path)
        if not doc:
            continue
        target = normalized_root(data_dir) / f"{sanitize_token(doc['doc_id'])}.json"
        write_json(target, doc)
        created += 1
    return {"scanned": len(files), "created": created}


def _iter_raw_files(*, raw_base: Path, source_type: Optional[str]) -> Iterable[Path]:
    if source_type:
        target = raw_base / sanitize_token(source_type)
        if not target.exists():
            return []
        return sorted(target.rglob("*.json"))
    return sorted(raw_base.rglob("*.json"))


def _normalize_one(*, payload: Dict[str, Any], raw_path: Path) -> Optional[Dict[str, Any]]:
    source_type = str(payload.get("source_type") or "").strip()
    source_id = str(payload.get("source_id") or "").strip()
    version = str(payload.get("version") or "snapshot")
    if source_type not in {"statute", "interpretation"}:
        return None
    if not source_id:
        return None
    doc_id = build_doc_id(source_type=source_type, source_id=source_id, version=version)

    if source_type == "statute":
        return _normalize_statute(payload=payload, raw_path=raw_path, doc_id=doc_id)
    return _normalize_interpretation(payload=payload, raw_path=raw_path, doc_id=doc_id)


def _normalize_statute(
    *,
    payload: Dict[str, Any],
    raw_path: Path,
    doc_id: str,
) -> Dict[str, Any]:
    detail = payload.get("detail") or {}
    search_result = payload.get("search_result") or {}
    title = (
        detail.get("title")
        or search_result.get("title")
        or search_result.get("법령명한글")
        or payload.get("source_id")
    )
    articles = detail.get("articles") or []
    article_texts = [_article_to_text(item) for item in articles]
    body = "\n\n".join(text for text in article_texts if text)
    summary_parts: List[str] = []
    if detail.get("doc_type"):
        summary_parts.append(f"구분: {detail['doc_type']}")
    if detail.get("ministry"):
        summary_parts.append(f"소관부처: {detail['ministry']}")
    if detail.get("promulgation_date"):
        summary_parts.append(f"공포일자: {detail['promulgation_date']}")
    if detail.get("enforcement_date"):
        summary_parts.append(f"시행일자: {detail['enforcement_date']}")

    return {
        "doc_id": doc_id,
        "source_type": "statute",
        "source_system": "law_go_kr",
        "source_id": payload.get("source_id"),
        "title": title,
        "summary": " | ".join(summary_parts),
        "body": body,
        "keywords": [
            k
            for k in [
                title,
                detail.get("doc_type"),
                detail.get("ministry"),
                detail.get("promulgation_number"),
            ]
            if k
        ],
        "issued_at": detail.get("promulgation_date"),
        "effective_at": detail.get("enforcement_date"),
        "agency_or_court": detail.get("ministry"),
        "status": detail.get("doc_type"),
        "version": payload.get("version"),
        "collected_at": payload.get("collected_at"),
        "raw_path": str(raw_path),
        "extra": {
            "promulgation_number": detail.get("promulgation_number"),
            "short_title": detail.get("short_title"),
            "article_count": len(articles),
        },
    }


def _article_to_text(article: Dict[str, Any]) -> str:
    no = article.get("article_no") or ""
    title = article.get("title") or ""
    content = article.get("content") or ""
    if content:
        return " ".join(part for part in [no, title, content] if part)
    paragraphs = article.get("paragraphs") or []
    lines: List[str] = []
    for para in paragraphs:
        number = para.get("number") or ""
        text = para.get("text") or ""
        clause = para.get("clause_text") or ""
        merged = " ".join(part for part in [number, clause, text] if part)
        if merged:
            lines.append(merged)
    joined = " ".join(lines)
    return " ".join(part for part in [no, title, joined] if part)


def _normalize_interpretation(
    *,
    payload: Dict[str, Any],
    raw_path: Path,
    doc_id: str,
) -> Dict[str, Any]:
    detail = payload.get("detail") or {}
    search_result = payload.get("search_result") or {}
    title = detail.get("title") or search_result.get("title") or payload.get("source_id")
    summary = detail.get("summary") or ""
    reply = detail.get("reply") or ""
    reason = detail.get("reason") or ""
    body = "\n\n".join([part for part in [summary, reply, reason] if part])
    return {
        "doc_id": doc_id,
        "source_type": "interpretation",
        "source_system": "law_go_kr",
        "source_id": payload.get("source_id"),
        "title": title,
        "summary": summary,
        "body": body,
        "keywords": [
            k
            for k in [
                title,
                detail.get("case_no"),
                detail.get("interpretation_org"),
                detail.get("inquiry_org"),
            ]
            if k
        ],
        "issued_at": detail.get("interpretation_date"),
        "effective_at": None,
        "agency_or_court": detail.get("interpretation_org") or detail.get("inquiry_org"),
        "status": "interpretation",
        "version": payload.get("version"),
        "collected_at": payload.get("collected_at"),
        "raw_path": str(raw_path),
        "extra": {
            "case_no": detail.get("case_no"),
            "reply_org": search_result.get("reply_org") or search_result.get("회신기관명"),
            "inquiry_org": detail.get("inquiry_org"),
        },
    }

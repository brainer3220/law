from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from packages.legal_tools.meili_client import request_json, resolve_index_uid


@dataclass
class MeiliDoc:
    """Search result payload returned by Meilisearch."""

    id: str
    doc_id: str
    title: str
    body: str
    snippet: str
    score: float
    source_path: str


def search_meilisearch(
    query: str,
    *,
    limit: int = 10,
    offset: int = 0,
    index_uid: Optional[str] = None,
) -> List[MeiliDoc]:
    """Execute a keyword search against Meilisearch."""

    if not query.strip():
        return []

    uid = resolve_index_uid(index_uid)
    payload = {
        "q": query,
        "limit": limit,
        "offset": max(0, offset),
        "attributesToHighlight": ["body"],
        "highlightPreTag": "<em>",
        "highlightPostTag": "</em>",
        "attributesToRetrieve": [
            "id",
            "doc_id",
            "title",
            "body",
            "source_path",
            "response_institute",
            "response_date",
        ],
    }
    try:
        data = request_json("POST", f"/indexes/{uid}/search", payload)
    except RuntimeError:
        return []

    hits = data.get("hits") or []
    out: List[MeiliDoc] = []
    for item in hits:
        formatted = item.get("_formatted") or {}
        snippet = formatted.get("body") or formatted.get("title") or ""
        score = 0.0
        if isinstance(raw_score := item.get("_rankingScore"), (int, float)):
            score = float(raw_score)
        out.append(
            MeiliDoc(
                id=str(item.get("id") or item.get("doc_id") or ""),
                doc_id=str(item.get("doc_id") or ""),
                title=str(item.get("title") or ""),
                body=str(item.get("body") or ""),
                snippet=str(snippet or ""),
                score=score,
                source_path=str(item.get("source_path") or ""),
            )
        )
    return out


__all__ = ["MeiliDoc", "search_meilisearch"]

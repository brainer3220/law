from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from packages.legal_tools.opensearch_client import request_json, resolve_index_name


@dataclass
class OpenSearchDoc:
    """Search result payload returned by OpenSearch."""

    id: str
    doc_id: str
    title: str
    body: str
    snippet: str
    score: float
    source_path: str


def _build_highlight_snippet(hit: dict) -> str:
    highlight = hit.get("highlight") or {}
    if not isinstance(highlight, dict):
        return ""
    for field in ("body", "title"):
        values = highlight.get(field)
        if isinstance(values, list) and values:
            return " ".join(str(v) for v in values if v)
    return ""


def search_opensearch(
    query: str,
    *,
    limit: int = 10,
    offset: int = 0,
    index: Optional[str] = None,
) -> List[OpenSearchDoc]:
    """Execute a keyword search against OpenSearch."""

    if not query.strip():
        return []

    index_name = resolve_index_name(index)
    payload = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",
                    "body",
                    "response_institute",
                    "response_date",
                    "task_type",
                ],
                "type": "best_fields",
            }
        },
        "from": max(0, offset),
        "size": max(0, limit),
        "_source": [
            "id",
            "doc_id",
            "title",
            "body",
            "source_path",
            "response_institute",
            "response_date",
            "task_type",
        ],
        "highlight": {
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
            "fields": {
                "body": {"fragment_size": 200, "number_of_fragments": 1},
                "title": {"fragment_size": 160, "number_of_fragments": 1},
            },
        },
    }
    try:
        data = request_json("POST", f"/{index_name}/_search", payload)
    except RuntimeError:
        return []

    hits_block = data.get("hits") or {}
    hits = hits_block.get("hits") if isinstance(hits_block, dict) else []
    out: List[OpenSearchDoc] = []
    for item in hits or []:
        if not isinstance(item, dict):
            continue
        source = item.get("_source") or {}
        snippet = _build_highlight_snippet(item) or (source.get("body") or source.get("title") or "")

        score = 0.0
        if isinstance(raw_score := item.get("_score"), (int, float)):
            score = float(raw_score)
        out.append(
            OpenSearchDoc(
                id=str(item.get("_id") or source.get("id") or source.get("doc_id") or ""),
                doc_id=str(source.get("doc_id") or source.get("id") or ""),
                title=str(source.get("title") or ""),
                body=str(source.get("body") or ""),
                snippet=str(snippet or ""),
                score=score,
                source_path=str(source.get("source_path") or ""),
            )
        )
    return out


__all__ = ["OpenSearchDoc", "search_opensearch"]

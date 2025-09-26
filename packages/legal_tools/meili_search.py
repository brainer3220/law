from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib import error, request


DEFAULT_MEILI_URL_ENV = (
    "MEILI_HTTP_ADDR",
    "MEILI_URL",
    "MEILISEARCH_URL",
)
DEFAULT_MEILI_KEY_ENV = (
    "MEILI_SEARCH_KEY",
    "MEILI_MASTER_KEY",
    "MEILI_API_KEY",
)
DEFAULT_INDEX_ENV = (
    "MEILI_INDEX",
    "MEILI_INDEX_UID",
)


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
    doc_class: str = ""
    document_type: str = ""
    response_institute: str = ""
    response_date: str = ""
    decision_date: str = ""
    task_type: str = ""
    statute_name: str = ""


def _first_env(keys: tuple[str, ...]) -> Optional[str]:
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return None


def _base_url() -> str:
    return _first_env(DEFAULT_MEILI_URL_ENV) or "http://localhost:7700"


def _api_key() -> Optional[str]:
    return _first_env(DEFAULT_MEILI_KEY_ENV)


def _index_uid(explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    env_value = _first_env(DEFAULT_INDEX_ENV)
    return env_value or "legal-docs"


def _request_json(method: str, path: str, payload: Optional[Dict] = None) -> Dict:
    url = _base_url().rstrip("/") + path
    headers = {"Content-Type": "application/json"}
    api_key = _api_key()
    if api_key:
        headers["X-Meili-API-Key"] = api_key
    data: Optional[bytes] = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            if not text:
                return {}
            return json.loads(text)
    except error.HTTPError as e:  # pragma: no cover - network failure
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Meilisearch {method} {path} failed: {e.status} {body}") from e
    except error.URLError as e:  # pragma: no cover - network failure
        raise RuntimeError(f"Failed to reach Meilisearch at {url}: {e.reason}") from e


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

    uid = _index_uid(index_uid)
    payload = {
        "q": query,
        "limit": int(limit),
        "offset": int(max(0, offset)),
        "attributesToHighlight": ["body"],
        "highlightPreTag": "<em>",
        "highlightPostTag": "</em>",
        "attributesToRetrieve": [
            "id",
            "doc_id",
            "title",
            "body",
            "source_path",
            "doc_class",
            "document_type",
            "response_institute",
            "response_date",
            "decision_date",
            "task_type",
            "statute_name",
        ],
    }
    data = _request_json("POST", f"/indexes/{uid}/search", payload)
    hits = data.get("hits") or []
    out: List[MeiliDoc] = []
    for item in hits:
        formatted = item.get("_formatted") or {}
        snippet = formatted.get("body") or formatted.get("title") or ""
        score = 0.0
        raw_score = item.get("_rankingScore")
        if isinstance(raw_score, (int, float)):
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
                doc_class=str(item.get("doc_class") or ""),
                document_type=str(item.get("document_type") or ""),
                response_institute=str(item.get("response_institute") or ""),
                response_date=str(item.get("response_date") or ""),
                decision_date=str(item.get("decision_date") or ""),
                task_type=str(item.get("task_type") or ""),
                statute_name=str(item.get("statute_name") or ""),
            )
        )
    return out


__all__ = ["MeiliDoc", "search_meilisearch"]

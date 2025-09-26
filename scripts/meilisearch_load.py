from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List, Optional
from urllib import error, request

from packages.env import load_env

load_env()


DEFAULT_MEILI_URL_ENV = (
    "MEILI_HTTP_ADDR",
    "MEILI_URL",
    "MEILISEARCH_URL",
)
DEFAULT_MEILI_KEY_ENV = (
    "MEILI_MASTER_KEY",
    "MEILI_API_KEY",
    "MEILI_ADMIN_KEY",
)
DEFAULT_INDEX_ENV = (
    "MEILI_INDEX",
    "MEILI_INDEX_UID",
)


def iter_json_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*.json")):
        if p.is_file():
            yield p


def build_title(info: dict) -> str:
    return str(
        info.get("title")
        or info.get("caseName")
        or info.get("casename")
        or info.get("doc_id")
        or ""
    )


def build_doc_id(info: dict, default: str) -> str:
    return str(
        info.get("doc_id")
        or info.get("precedId")
        or info.get("caseNum")
        or info.get("case_id")
        or default
    )


def build_body(data: dict) -> str:
    info = data.get("info", {}) or {}
    task = data.get("taskinfo", {}) or {}

    has_task = any(
        bool(task.get(k)) for k in ("instruction", "sentences", "output", "input")
    )
    if has_task:
        parts = [
            str(info.get("doc_id", "")),
            str(info.get("title", "")),
            str(info.get("response_institute", "")),
            str(info.get("response_date", "")),
            str(info.get("taskType", "")),
            str(task.get("instruction", "")),
            " ".join(str(s) for s in (task.get("sentences") or []) if s),
            str(task.get("output", "")),
        ]
        return "\n".join(p for p in parts if p)

    full_text = info.get("fullText")
    header_bits = [
        str(info.get("caseName", "")),
        str(info.get("caseNum", "")),
        str(info.get("courtName", "")),
        str(info.get("sentenceDate", "")),
    ]
    header = " | ".join([b for b in header_bits if b])
    if full_text:
        return "\n".join([p for p in (header, str(full_text)) if p])

    info_pairs = []
    for k in (
        "caseName",
        "caseNum",
        "courtName",
        "sentenceDate",
        "lawClass",
        "DocuType",
        "sentenceType",
    ):
        v = info.get(k)
        if v:
            info_pairs.append(f"{k}: {v}")
    return "\n".join(info_pairs)


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


def _request_json(method: str, path: str, payload: Optional[dict] = None) -> dict:
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
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"Meilisearch {method} {path} failed: {e.status} {body}") from e
    except error.URLError as e:
        raise RuntimeError(f"Failed to reach Meilisearch at {url}: {e.reason}") from e


def ensure_index(uid: str) -> None:
    try:
        _request_json("GET", f"/indexes/{uid}")
        return
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise
    _request_json("POST", "/indexes", {"uid": uid, "primaryKey": "id"})
    settings = {
        "searchableAttributes": ["title", "body", "response_institute", "response_date", "task_type"],
        "displayedAttributes": [
            "id",
            "doc_id",
            "title",
            "body",
            "response_institute",
            "response_date",
            "task_type",
            "source_path",
        ],
        "filterableAttributes": ["response_institute", "response_date", "task_type"],
    }
    _request_json("PATCH", f"/indexes/{uid}/settings", settings)


def collect_documents(data_dir: Path) -> List[dict]:
    documents: List[dict] = []
    for path in iter_json_files(data_dir):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        info = raw.get("info", {}) or {}
        task = raw.get("taskinfo", {}) or {}
        doc_id = build_doc_id(info, str(path))
        title = build_title(info)
        body = build_body(raw)
        documents.append(
            {
                "id": doc_id,
                "doc_id": doc_id,
                "title": title,
                "body": body,
                "response_institute": str(info.get("response_institute") or info.get("courtName") or ""),
                "response_date": str(info.get("response_date") or info.get("sentenceDate") or ""),
                "task_type": str(info.get("taskType") or ""),
                "source_path": str(path),
                "meta": {"info": info, "taskinfo": task},
            }
        )
    return documents


def chunked(seq: List[dict], size: int) -> Iterable[List[dict]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def upload_documents(uid: str, documents: List[dict], *, batch_size: int = 500) -> None:
    for batch in chunked(documents, batch_size):
        _request_json("POST", f"/indexes/{uid}/documents", batch)


def main(*, data_dir: Optional[str] = None, index_uid: Optional[str] = None) -> int:
    target_dir = Path(data_dir or os.getenv("LAW_MEILI_DATA_DIR") or "data/meilisearch")
    if not target_dir.exists():
        print(f"Data directory not found: {target_dir}")
        return 2

    uid = _index_uid(index_uid)
    ensure_index(uid)

    documents = collect_documents(target_dir)
    if not documents:
        print(f"No documents discovered under {target_dir}")
        return 1

    upload_documents(uid, documents)
    print(f"Indexed {len(documents)} documents into Meilisearch index '{uid}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

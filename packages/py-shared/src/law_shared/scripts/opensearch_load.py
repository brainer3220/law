from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import quote

try:  # pragma: no cover - optional dependency for CLI UX
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback when tqdm is unavailable
    TQDM_AVAILABLE = False

    def tqdm(iterable, **_kwargs):  # type: ignore
        return iterable

from law_shared.env import load_env
from law_shared.legal_tools.opensearch_client import request_json, resolve_index_name

load_env()


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
        if v := info.get(k):
            info_pairs.append(f"{k}: {v}")
    return "\n".join(info_pairs)


def ensure_index(name: str) -> None:
    try:
        request_json("GET", f"/{name}")
        return
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise

    body = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            }
        },
        "mappings": {
            "dynamic": "true",
            "properties": {
                "id": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                "title": {"type": "text"},
                "body": {"type": "text"},
                "response_institute": {"type": "keyword"},
                "response_date": {"type": "keyword"},
                "task_type": {"type": "keyword"},
                "source_path": {"type": "keyword"},
                "meta": {"type": "object", "enabled": False},
            },
        },
    }
    request_json("PUT", f"/{name}", body)


def collect_documents(data_dir: Path, *, show_progress: bool = False) -> List[dict]:
    logger = logging.getLogger(__name__)
    documents: List[dict] = []
    skipped: list[Path] = []
    paths = list(iter_json_files(data_dir))
    iterator: Iterable[Path] = paths
    if show_progress and paths:
        if TQDM_AVAILABLE:
            iterator = tqdm(paths, desc="Reading documents", unit="file")
        else:
            logger.info(
                "Install the 'tqdm' package to see document ingestion progress bars."
            )
    for path in iterator:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("Skipping file with invalid JSON: %s (%s)", path, exc)
            skipped.append(path)
            continue
        except OSError as exc:
            logger.warning("Skipping file that could not be read: %s (%s)", path, exc)
            skipped.append(path)
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
    if skipped:
        logger.info("Skipped %d files due to parse issues.", len(skipped))
    return documents


def chunked(seq: List[dict], size: int) -> Iterable[List[dict]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def upload_documents(
    index_name: str,
    documents: List[dict],
    *,
    batch_size: int = 500,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    show_progress: bool = True,
) -> None:
    logger = logging.getLogger(__name__)
    total = (len(documents) + batch_size - 1) // batch_size if documents else 0
    batches = chunked(documents, batch_size)
    iterator: Iterable[List[dict]]
    if show_progress and total:
        if TQDM_AVAILABLE:
            iterator = tqdm(
                batches, total=total, desc="Uploading documents", unit="batch"
            )
        else:
            logger.info("Install the 'tqdm' package to see upload progress bars.")
            iterator = batches
    else:
        iterator = batches

    for batch in iterator:
        for attempt in range(1, max_retries + 1):
            try:
                for doc in batch:
                    doc_id = str(doc.get("id") or doc.get("doc_id") or "").strip()
                    if not doc_id:
                        raise RuntimeError("Document is missing an 'id' field")
                    path = f"/{index_name}/_doc/{quote(doc_id, safe='')}"
                    request_json("PUT", path, doc)
                break
            except RuntimeError as exc:
                if attempt == max_retries:
                    logger.error(
                        "Failed to upload batch after %d attempts: %s", max_retries, exc
                    )
                    raise
                logger.warning(
                    "Error uploading batch (attempt %d/%d): %s", attempt, max_retries, exc
                )
                time.sleep(retry_delay)


def main(*, data_dir: Optional[str] = None, index_name: Optional[str] = None) -> int:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
        )

    target_dir = Path(
        data_dir
        or os.getenv("LAW_SEARCH_DATA_DIR")
        or os.getenv("LAW_MEILI_DATA_DIR")
        or "data/opensearch"
    )
    if not target_dir.exists():
        print(f"Data directory not found: {target_dir}")
        return 2

    name = resolve_index_name(index_name)
    ensure_index(name)

    documents = collect_documents(target_dir, show_progress=True)
    if not documents:
        print(f"No documents discovered under {target_dir}")
        return 1

    upload_documents(name, documents, show_progress=True)
    print(f"Indexed {len(documents)} documents into OpenSearch index '{name}'.")
    return 0

__all__ = [
    "collect_documents",
    "chunked",
    "ensure_index",
    "main",
    "upload_documents",
]


if __name__ == "__main__":
    raise SystemExit(main())

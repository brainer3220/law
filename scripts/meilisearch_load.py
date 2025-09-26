from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Iterable, List, Optional

try:  # pragma: no cover - optional dependency for CLI UX
    from tqdm import tqdm
except ImportError:  # pragma: no cover - fallback when tqdm is unavailable
    def tqdm(iterable, **_kwargs):  # type: ignore
        return iterable

from packages.env import load_env
from packages.legal_tools.meili_client import request_json, resolve_index_uid

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


def ensure_index(uid: str) -> None:
    try:
        request_json("GET", f"/indexes/{uid}")
        return
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise
    request_json("POST", "/indexes", {"uid": uid, "primaryKey": "id"})
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
    request_json("PATCH", f"/indexes/{uid}/settings", settings)


def collect_documents(data_dir: Path) -> List[dict]:
    logger = logging.getLogger(__name__)
    documents: List[dict] = []
    skipped: list[Path] = []
    for path in iter_json_files(data_dir):
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
    uid: str,
    documents: List[dict],
    *,
    batch_size: int = 500,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    show_progress: bool = True,
) -> None:
    logger = logging.getLogger(__name__)
    batches = chunked(documents, batch_size)
    total = (len(documents) + batch_size - 1) // batch_size if documents else 0
    iterator = (
        tqdm(batches, total=total, desc="Uploading documents", unit="batch")
        if show_progress and total
        else batches
    )

    for batch in iterator:
        for attempt in range(1, max_retries + 1):
            try:
                request_json("POST", f"/indexes/{uid}/documents", batch)
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


def main(*, data_dir: Optional[str] = None, index_uid: Optional[str] = None) -> int:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    target_dir = Path(data_dir or os.getenv("LAW_MEILI_DATA_DIR") or "data/meilisearch")
    if not target_dir.exists():
        print(f"Data directory not found: {target_dir}")
        return 2

    uid = resolve_index_uid(index_uid)
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

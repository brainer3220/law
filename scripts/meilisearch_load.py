from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
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

CSV_ID_FIELDS: Tuple[str, ...] = (
    "doc_id",
    "DocID",
    "precedId",
    "결정례일련번호",
    "법령일련번호",
    "문서ID",
)
CSV_TEXT_FIELDS: Tuple[str, ...] = (
    "내용",
    "text",
    "sentence",
    "body",
)
CSV_ORDER_FIELDS: Tuple[str, ...] = (
    "문장번호",
    "sentence_no",
    "order",
)
CSV_SECTION_FIELDS: Tuple[str, ...] = (
    "구분",
    "section",
    "항",
)
CSV_TITLE_FIELDS: Tuple[str, ...] = (
    "제목",
    "법령명",
    "statute_name",
    "caseName",
)


def iter_data_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in {".json", ".csv"} and p.is_file():
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
            join_sentences(task.get("sentences")),
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
    more_sentences = join_sentences(info.get("sentences"))
    if more_sentences:
        info_pairs.append(more_sentences)
    return "\n".join(info_pairs)


def join_sentences(value: object) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Sequence):
        parts = []
        for item in value:
            if isinstance(item, (list, tuple)):
                parts.append(" ".join(str(x) for x in item if x))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    return str(value)


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
        "searchableAttributes": [
            "title",
            "body",
            "response_institute",
            "response_date",
            "task_type",
            "doc_class",
            "document_type",
            "statute_name",
        ],
        "displayedAttributes": [
            "id",
            "doc_id",
            "title",
            "body",
            "doc_class",
            "document_type",
            "response_institute",
            "response_date",
            "decision_date",
            "task_type",
            "statute_name",
            "source_path",
        ],
        "filterableAttributes": [
            "doc_class",
            "document_type",
            "response_institute",
            "response_date",
            "decision_date",
            "task_type",
            "statute_name",
        ],
    }
    _request_json("PATCH", f"/indexes/{uid}/settings", settings)


def collect_documents(data_dir: Path) -> List[dict]:
    documents: List[dict] = []
    for path in iter_data_files(data_dir):
        if path.suffix.lower() == ".json":
            documents.extend(_collect_from_json(path))
        elif path.suffix.lower() == ".csv":
            documents.extend(_collect_from_csv(path))
    return documents


def _collect_from_json(path: Path) -> List[dict]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    records: List[dict]
    if isinstance(raw, list):
        records = [r for r in raw if isinstance(r, dict)]
    elif isinstance(raw, dict):
        records = [raw]
    else:
        return []

    documents: List[dict] = []
    for record in records:
        info = record.get("info", {}) if isinstance(record, dict) else {}
        if not isinstance(info, dict):
            info = {}
        task = record.get("taskinfo", {}) if isinstance(record, dict) else {}
        if not isinstance(task, dict):
            task = {}

        doc_id = build_doc_id(info, str(path))
        title = build_title(info)
        body = build_body(record)
        doc_class = str(info.get("doc_class") or record.get("doc_class") or "")
        document_type = str(info.get("document_type") or record.get("document_type") or "")
        documents.append(
            {
                "id": doc_id,
                "doc_id": doc_id,
                "title": title,
                "body": body,
                "doc_class": doc_class,
                "document_type": document_type,
                "response_institute": str(info.get("response_institute") or info.get("courtName") or ""),
                "response_date": str(info.get("response_date") or info.get("sentenceDate") or ""),
                "decision_date": str(info.get("decision_date") or ""),
                "task_type": str(info.get("taskType") or task.get("taskType") or ""),
                "statute_name": str(info.get("statute_name") or ""),
                "source_path": str(path),
                "meta": {"info": info, "taskinfo": task},
            }
        )
    return documents


def _collect_from_csv(path: Path) -> List[dict]:
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames or []
            if not fieldnames:
                return []

            doc_id_field = _guess_field(fieldnames, CSV_ID_FIELDS)
            text_field = _guess_field(fieldnames, CSV_TEXT_FIELDS)
            if not doc_id_field or not text_field:
                return []

            order_field = _guess_field(fieldnames, CSV_ORDER_FIELDS)
            section_field = _guess_field(fieldnames, CSV_SECTION_FIELDS)
            title_field = _guess_field(fieldnames, CSV_TITLE_FIELDS)

            rows_by_doc: Dict[str, List[dict]] = defaultdict(list)
            for row in reader:
                doc_key = str(row.get(doc_id_field) or "").strip()
                if not doc_key:
                    continue
                rows_by_doc[doc_key].append(row)
    except Exception:
        return []

    documents: List[dict] = []
    for doc_id, rows in rows_by_doc.items():
        sections: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        metadata: Dict[str, str] = {}
        title_value = ""
        first_sentence: Optional[str] = None
        for idx, row in enumerate(rows):
            text = str(row.get(text_field) or "").strip()
            if not text:
                continue
            order_value = _parse_order(row.get(order_field) if order_field else idx + 1)
            section_name = str(row.get(section_field) or "").strip()
            sections[section_name].append((order_value, text))
            if section_field and section_name and section_field not in metadata:
                metadata.setdefault(section_field, section_name)
            if first_sentence is None:
                first_sentence = text
            if not title_value and title_field:
                title_value = str(row.get(title_field) or "").strip()
            for key, value in row.items():
                if key in {doc_id_field, text_field, order_field, section_field}:
                    continue
                if not value:
                    continue
                metadata.setdefault(key, str(value))

        body_parts: List[str] = []
        for section_name, sentences in sections.items():
            sentences.sort(key=lambda item: item[0])
            text_block = "\n".join(sentence for _, sentence in sentences if sentence)
            if not text_block:
                continue
            if section_name:
                body_parts.append(f"[{section_name}]\n{text_block}")
            else:
                body_parts.append(text_block)
        body = "\n\n".join(body_parts)
        if not body:
            continue

        doc_class = metadata.get("doc_class") or metadata.get("DocClass")
        if not doc_class:
            doc_class = "statute" if "법령일련번호" in rows[0] else "precedent"
        document_type = metadata.get("document_type") or metadata.get("DocumentType") or metadata.get("자료구분")
        title = title_value or metadata.get("제목") or metadata.get("법령명") or metadata.get("statute_name")
        if not title and first_sentence:
            title = first_sentence[:120]

        document = {
            "id": doc_id,
            "doc_id": doc_id,
            "title": title or doc_id,
            "body": body,
            "doc_class": doc_class,
            "document_type": document_type or metadata.get("구분", ""),
            "response_institute": metadata.get("response_institute", ""),
            "response_date": metadata.get("response_date", ""),
            "task_type": metadata.get("taskType", ""),
            "statute_name": metadata.get("법령명") or metadata.get("statute_name", ""),
            "source_path": str(path),
            "meta": {"csv_fieldnames": fieldnames, "csv_metadata": metadata},
        }
        documents.append(document)
    return documents


def _guess_field(fieldnames: Sequence[str], candidates: Tuple[str, ...]) -> Optional[str]:
    lowered = {name.lower(): name for name in fieldnames}
    for cand in candidates:
        if cand in fieldnames:
            return cand
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    return None


def _parse_order(raw: object) -> float:
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
        if digits:
            try:
                return float(digits)
            except ValueError:
                return 0.0
    return 0.0


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

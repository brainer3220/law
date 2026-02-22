from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from law_shared.legal_tools.file_store import ensure_layout, index_root, normalized_root, read_json


def index_db_path(data_dir: Path) -> Path:
    return index_root(data_dir) / "search.db"


def rebuild_index(*, data_dir: Path) -> Dict[str, int]:
    ensure_layout(data_dir)
    db_path = index_db_path(data_dir)
    conn = sqlite3.connect(str(db_path))
    try:
        _init_schema(conn)
        conn.execute("DELETE FROM docs_fts")
        conn.execute("DELETE FROM documents")
        count = _upsert_from_files(conn=conn, files=_iter_normalized_files(data_dir))
        conn.commit()
        return {"indexed": count}
    finally:
        conn.close()


def update_index(*, data_dir: Path) -> Dict[str, int]:
    ensure_layout(data_dir)
    db_path = index_db_path(data_dir)
    conn = sqlite3.connect(str(db_path))
    try:
        _init_schema(conn)
        count = _upsert_from_files(conn=conn, files=_iter_normalized_files(data_dir))
        conn.commit()
        return {"indexed": count}
    finally:
        conn.close()


def _iter_normalized_files(data_dir: Path) -> Iterable[Path]:
    base = normalized_root(data_dir)
    if not base.exists():
        return []
    return sorted(base.glob("*.json"))


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            source_type TEXT,
            title TEXT,
            body TEXT,
            summary TEXT,
            keywords TEXT,
            agency_or_court TEXT,
            status TEXT,
            issued_at TEXT,
            effective_at TEXT,
            year INTEGER,
            version TEXT,
            collected_at TEXT,
            source_id TEXT,
            raw_path TEXT,
            normalized_path TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts
        USING fts5(
            doc_id UNINDEXED,
            title,
            body,
            summary,
            keywords,
            tokenize='unicode61'
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_agency ON documents(agency_or_court)"
    )


def _upsert_from_files(*, conn: sqlite3.Connection, files: Iterable[Path]) -> int:
    count = 0
    for path in files:
        payload = read_json(path)
        doc_id = str(payload.get("doc_id") or "").strip()
        if not doc_id:
            continue
        title = str(payload.get("title") or "")
        body = str(payload.get("body") or "")
        summary = str(payload.get("summary") or "")
        keywords = _keywords_as_text(payload.get("keywords"))
        issued_at = payload.get("issued_at")
        year = _extract_year(issued_at)
        row = {
            "doc_id": doc_id,
            "source_type": payload.get("source_type"),
            "title": title,
            "body": body,
            "summary": summary,
            "keywords": keywords,
            "agency_or_court": payload.get("agency_or_court"),
            "status": payload.get("status"),
            "issued_at": issued_at,
            "effective_at": payload.get("effective_at"),
            "year": year,
            "version": payload.get("version"),
            "collected_at": payload.get("collected_at"),
            "source_id": payload.get("source_id"),
            "raw_path": payload.get("raw_path"),
            "normalized_path": str(path),
        }
        _upsert_document(conn, row)
        _upsert_fts(conn, row)
        count += 1
    return count


def _upsert_document(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO documents (
            doc_id, source_type, title, body, summary, keywords,
            agency_or_court, status, issued_at, effective_at, year,
            version, collected_at, source_id, raw_path, normalized_path
        ) VALUES (
            :doc_id, :source_type, :title, :body, :summary, :keywords,
            :agency_or_court, :status, :issued_at, :effective_at, :year,
            :version, :collected_at, :source_id, :raw_path, :normalized_path
        )
        ON CONFLICT(doc_id) DO UPDATE SET
            source_type=excluded.source_type,
            title=excluded.title,
            body=excluded.body,
            summary=excluded.summary,
            keywords=excluded.keywords,
            agency_or_court=excluded.agency_or_court,
            status=excluded.status,
            issued_at=excluded.issued_at,
            effective_at=excluded.effective_at,
            year=excluded.year,
            version=excluded.version,
            collected_at=excluded.collected_at,
            source_id=excluded.source_id,
            raw_path=excluded.raw_path,
            normalized_path=excluded.normalized_path
        """,
        row,
    )


def _upsert_fts(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    conn.execute("DELETE FROM docs_fts WHERE doc_id = ?", (row["doc_id"],))
    conn.execute(
        """
        INSERT INTO docs_fts (doc_id, title, body, summary, keywords)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            row["doc_id"],
            row["title"],
            row["body"],
            row["summary"],
            row["keywords"],
        ),
    )


def _keywords_as_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    return str(value or "")


def _extract_year(value: Optional[str]) -> Optional[int]:
    text = (value or "").strip()
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None

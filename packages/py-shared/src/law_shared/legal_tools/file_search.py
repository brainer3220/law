from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from law_shared.legal_tools.file_index_sqlite import index_db_path


@dataclass
class FileSearchHit:
    doc_id: str
    title: str
    score: float
    snippet: str
    source_type: str
    source_path: str


def search_local_index(
    *,
    data_dir: Path,
    query: str,
    limit: int = 10,
    offset: int = 0,
    source_type: Optional[str] = None,
    year: Optional[int] = None,
    agency: Optional[str] = None,
    status: Optional[str] = None,
) -> List[FileSearchHit]:
    db_path = index_db_path(data_dir)
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        if (query or "").strip():
            return _search_with_fts(
                conn=conn,
                query=query,
                limit=limit,
                offset=offset,
                source_type=source_type,
                year=year,
                agency=agency,
                status=status,
            )
        return _search_recent(
            conn=conn,
            limit=limit,
            offset=offset,
            source_type=source_type,
            year=year,
            agency=agency,
            status=status,
        )
    finally:
        conn.close()


def _search_with_fts(
    *,
    conn: sqlite3.Connection,
    query: str,
    limit: int,
    offset: int,
    source_type: Optional[str],
    year: Optional[int],
    agency: Optional[str],
    status: Optional[str],
) -> List[FileSearchHit]:
    clauses = ["docs_fts MATCH ?"]
    params: List[object] = [query]
    _append_filters(
        clauses=clauses,
        params=params,
        source_type=source_type,
        year=year,
        agency=agency,
        status=status,
    )
    where_clause = " AND ".join(clauses)
    sql = f"""
        SELECT
            d.doc_id,
            d.title,
            d.source_type,
            d.normalized_path,
            bm25(docs_fts) AS score,
            snippet(docs_fts, 2, '[', ']', '...', 32) AS snippet,
            d.summary,
            d.body
        FROM docs_fts
        JOIN documents d ON d.doc_id = docs_fts.doc_id
        WHERE {where_clause}
        ORDER BY score
        LIMIT ? OFFSET ?
    """
    params.extend([max(1, int(limit)), max(0, int(offset))])
    rows = conn.execute(sql, params).fetchall()
    return [_to_hit(row) for row in rows]


def _search_recent(
    *,
    conn: sqlite3.Connection,
    limit: int,
    offset: int,
    source_type: Optional[str],
    year: Optional[int],
    agency: Optional[str],
    status: Optional[str],
) -> List[FileSearchHit]:
    clauses: List[str] = []
    params: List[object] = []
    _append_filters(
        clauses=clauses,
        params=params,
        source_type=source_type,
        year=year,
        agency=agency,
        status=status,
    )
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT
            doc_id,
            title,
            source_type,
            normalized_path,
            0.0 AS score,
            summary AS snippet,
            summary,
            body
        FROM documents
        {where_clause}
        ORDER BY collected_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([max(1, int(limit)), max(0, int(offset))])
    rows = conn.execute(sql, params).fetchall()
    return [_to_hit(row) for row in rows]


def _append_filters(
    *,
    clauses: List[str],
    params: List[object],
    source_type: Optional[str],
    year: Optional[int],
    agency: Optional[str],
    status: Optional[str],
) -> None:
    if source_type:
        clauses.append("d.source_type = ?" if _has_fts_clause(clauses) else "source_type = ?")
        params.append(source_type)
    if year is not None:
        clauses.append("d.year = ?" if _has_fts_clause(clauses) else "year = ?")
        params.append(int(year))
    if agency:
        clauses.append(
            "d.agency_or_court LIKE ?"
            if _has_fts_clause(clauses)
            else "agency_or_court LIKE ?"
        )
        params.append(f"%{agency}%")
    if status:
        clauses.append("d.status = ?" if _has_fts_clause(clauses) else "status = ?")
        params.append(status)


def _has_fts_clause(clauses: List[str]) -> bool:
    return any("docs_fts" in clause or "d." in clause for clause in clauses) or (
        len(clauses) > 0 and clauses[0].startswith("docs_fts MATCH")
    )


def _to_hit(row: sqlite3.Row) -> FileSearchHit:
    snippet = str(row["snippet"] or row["summary"] or row["body"] or "")
    if len(snippet) > 1200:
        snippet = snippet[:1197] + "..."
    return FileSearchHit(
        doc_id=str(row["doc_id"]),
        title=str(row["title"] or row["doc_id"]),
        score=float(row["score"] or 0.0),
        snippet=snippet,
        source_type=str(row["source_type"] or ""),
        source_path=str(row["normalized_path"] or ""),
    )

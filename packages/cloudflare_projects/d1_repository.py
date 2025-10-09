from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from .bindings import D1Binding
from .config import CloudflareProjectsConfig


@dataclass(frozen=True)
class ChunkCandidate:
    """Result row from doc_chunks_fts with bm25 score and snippet."""

    rowid: int
    doc_id: str
    page: Optional[int]
    heading: Optional[str]
    snippet: str
    bm25_score: float
    recency_score: float
    click_score: float

    @property
    def effective_score(self) -> float:
        return self.bm25_score - self.recency_score - self.click_score


@dataclass(frozen=True)
class InstructionVersion:
    version: int
    content: str
    created_by: Optional[str]
    created_at: Optional[str]


@dataclass(frozen=True)
class ProjectMemory:
    key: str
    value: str
    source: Optional[str]
    expires_at: Optional[str]
    confidence: Optional[float]


class D1Repository:
    """Data-access helpers for D1 tables and the FTS virtual table."""

    _fts_escape_re = re.compile(r"([\"'`])")

    def __init__(self, d1: D1Binding, cfg: CloudflareProjectsConfig) -> None:
        self._d1 = d1
        self._cfg = cfg

    # ---------------------- Search helpers ----------------------
    def build_match_query(self, query: str, *, boosts: Optional[Sequence[str]] = None) -> str:
        """Escapes a free-form query and appends field boosting tokens."""

        trimmed = query.strip()
        if not trimmed:
            return ""

        escaped = self._fts_escape_re.sub(r"\\\1", trimmed)
        tokens = [t for t in re.split(r"\s+", escaped) if t]
        if not tokens:
            return ""

        wildcards = [f'"{token}" OR {token}*' for token in tokens]
        combined = " AND ".join(f"({fragment})" for fragment in wildcards)
        suffix = boosts or self._cfg.fts.default_query_boosts
        boost_suffix = " ".join(suffix)
        return f"({combined}) {boost_suffix}".strip()

    async def search_candidates(
        self,
        project_id: str,
        query: str,
        *,
        limit: Optional[int] = None,
    ) -> List[ChunkCandidate]:
        """Retrieve BM25-ranked candidates for reranking."""

        match_query = self.build_match_query(query)
        if not match_query:
            return []

        limit = limit or self._cfg.fts.max_candidates
        sql = f"""
            SELECT
                doc_chunks_fts.rowid AS rowid,
                doc_chunks_fts.doc_id AS doc_id,
                doc_chunks_fts.page AS page,
                doc_chunks_fts.heading AS heading,
                snippet(
                    {self._cfg.doc_chunks_table},
                    -1,
                    ?,
                    ?,
                    ?,
                    ?
                ) AS snippet,
                bm25({self._cfg.doc_chunks_table}) AS bm25_score,
                COALESCE(meta.recency_score, 0) * ? AS recency_score,
                COALESCE(meta.click_score, 0) * ? AS click_score
            FROM {self._cfg.doc_chunks_table}
            LEFT JOIN {self._cfg.doc_chunks_meta_table} AS meta
              ON meta.chunk_rowid = {self._cfg.doc_chunks_table}.rowid
            WHERE project_id = ? AND {self._cfg.doc_chunks_table} MATCH ?
            ORDER BY (bm25_score - recency_score - click_score) ASC
            LIMIT ?
        """

        stmt = (
            self._d1.prepare(sql)
            .bind(
                self._cfg.fts.snippet_prefix,
                self._cfg.fts.snippet_suffix,
                self._cfg.fts.snippet_ellipsis,
                self._cfg.fts.snippet_tokens,
                self._cfg.fts.recency_weight,
                self._cfg.fts.click_weight,
                project_id,
                match_query,
                limit,
            )
        )
        result = await stmt.all()
        rows = result.get("results", []) if isinstance(result, dict) else []
        candidates: List[ChunkCandidate] = []
        for row in rows:
            candidates.append(
                ChunkCandidate(
                    rowid=int(row["rowid"]),
                    doc_id=row["doc_id"],
                    page=row.get("page"),
                    heading=row.get("heading"),
                    snippet=row.get("snippet", ""),
                    bm25_score=float(row.get("bm25_score", 0.0)),
                    recency_score=float(row.get("recency_score", 0.0)),
                    click_score=float(row.get("click_score", 0.0)),
                )
            )
        return candidates

    async def record_click_feedback(self, rowids: Iterable[int]) -> None:
        """Increment click signals for doc chunks."""

        rowid_list = list(rowids)
        if not rowid_list:
            return

        sql = f"""
            INSERT INTO {self._cfg.doc_chunks_meta_table} (chunk_rowid, click_score)
            VALUES (?, 1.0)
            ON CONFLICT(chunk_rowid) DO UPDATE SET click_score = click_score + 1.0
        """
        statements = [self._d1.prepare(sql).bind(rowid) for rowid in rowid_list]
        await self._d1.batch(statements)

    # ---------------------- Project memory ----------------------
    async def load_project_instructions(self, project_id: str) -> List[InstructionVersion]:
        sql = f"""
            SELECT version, content, created_by, created_at
            FROM {self._cfg.instructions_table}
            WHERE project_id = ?
            ORDER BY version DESC
        """
        stmt = self._d1.prepare(sql).bind(project_id)
        result = await stmt.all()
        rows = result.get("results", []) if isinstance(result, dict) else []
        return [
            InstructionVersion(
                version=int(row["version"]),
                content=row["content"],
                created_by=row.get("created_by"),
                created_at=row.get("created_at"),
            )
            for row in rows
        ]

    async def load_project_memories(self, project_id: str) -> List[ProjectMemory]:
        sql = f"""
            SELECT key, value, source, expires_at, confidence
            FROM {self._cfg.memories_table}
            WHERE project_id = ?
        """
        stmt = self._d1.prepare(sql).bind(project_id)
        result = await stmt.all()
        rows = result.get("results", []) if isinstance(result, dict) else []
        return [
            ProjectMemory(
                key=row["key"],
                value=row["value"],
                source=row.get("source"),
                expires_at=row.get("expires_at"),
                confidence=float(row["confidence"]) if row.get("confidence") is not None else None,
            )
            for row in rows
        ]

    # ---------------------- Upsert helpers ----------------------
    async def upsert_document_chunk(
        self,
        *,
        doc_id: str,
        project_id: str,
        page: Optional[int],
        heading: Optional[str],
        body: str,
    ) -> None:
        sql = f"""
            INSERT INTO {self._cfg.doc_chunks_table}(doc_id, project_id, page, heading, body)
            VALUES (?, ?, ?, ?, ?)
        """
        await self._d1.prepare(sql).bind(doc_id, project_id, page, heading, body).run()


__all__ = [
    "ChunkCandidate",
    "D1Repository",
    "InstructionVersion",
    "ProjectMemory",
]

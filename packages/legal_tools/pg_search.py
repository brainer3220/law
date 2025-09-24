"""Postgres BM25 search helpers with multi-variant fusion."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from typing import Dict, List, Sequence, Tuple

from packages.legal_tools.lexical import LexicalVariant, build_query_variants

__all__ = ["PgDoc", "search_bm25", "build_query_variants"]


def ensure_psycopg():
    try:
        import psycopg  # type: ignore

        return psycopg
    except Exception as e:  # pragma: no cover - import guard
        raise RuntimeError(
            "psycopg is required for Postgres search. Install with `uv pip install psycopg[binary]`."
        ) from e


@dataclass
class PgDoc:
    id: str
    doc_id: str
    title: str
    path: str
    body: str
    snippet: str
    score: float
    score_components: Dict[str, float] = field(default_factory=dict)


def _has_extension(conn, name: str) -> bool:
    try:
        row = conn.execute("SELECT 1 FROM pg_extension WHERE extname = %s", (name,)).fetchone()
        return bool(row)
    except Exception:
        return False


def _row_to_doc(row: Tuple[object, ...]) -> PgDoc:
    return PgDoc(
        id=str(row[0] or ""),
        doc_id=str(row[1] or ""),
        title=str(row[2] or ""),
        path=str(row[3] or ""),
        body=str(row[4] or ""),
        snippet=str(row[5] or ""),
        score=float(row[6] or 0.0),
    )


def _pgsearch_where(fields: Sequence[str]) -> str:
    search_fields = tuple(fields) or ("title", "body")
    return " OR ".join(f"{field} @@@ %(q)s" for field in search_fields)


_TS_VECTOR = "setweight(to_tsvector(cfg.cf, COALESCE(title,'')), 'A') || setweight(to_tsvector(cfg.cf, COALESCE(body,'')), 'D')"


def _fts_where(fields: Sequence[str]) -> str:
    search_fields = tuple(fields) or ("title", "body")
    return " OR ".join(
        f"to_tsvector(cfg.cf, COALESCE({field},'')) @@ plainto_tsquery(cfg.cf, %(q)s)" for field in search_fields
    )


def _execute_variant(
    conn,
    variant: LexicalVariant,
    limit: int,
    *,
    use_pg_search: bool,
) -> List[PgDoc]:
    params = {"q": variant.query, "k": int(limit)}
    if use_pg_search:
        sql = f"""
            SELECT id::text,
                   COALESCE(doc_id, ''),
                   COALESCE(title, ''),
                   COALESCE(path, ''),
                   COALESCE(body, ''),
                   paradedb.snippet(body, %(q)s) AS snippet,
                   paradedb.score(id) AS score
            FROM public.legal_docs
            WHERE {_pgsearch_where(variant.fields)}
            ORDER BY score DESC
            LIMIT %(k)s
        """
        rows = conn.execute(sql, params).fetchall()
    else:
        sql = f"""
            WITH cfg AS (
              SELECT 'simple'::regconfig AS cf
            )
            SELECT id::text,
                   COALESCE(doc_id, ''),
                   COALESCE(title, ''),
                   COALESCE(path, ''),
                   COALESCE(body, ''),
                   ts_headline(
                       cfg.cf,
                       body,
                       plainto_tsquery(cfg.cf, %(q)s),
                       'MaxFragments=2, MinWords=15, MaxWords=40'
                   ) AS snippet,
                   ts_rank_cd({_TS_VECTOR}, plainto_tsquery(cfg.cf, %(q)s), 32) +
                     CASE
                       WHEN to_tsvector(cfg.cf, COALESCE(title,'')) @@ plainto_tsquery(cfg.cf, %(q)s)
                       THEN 0.1
                       ELSE 0
                     END AS score
            FROM public.legal_docs, cfg
            WHERE {_fts_where(variant.fields)}
            ORDER BY score DESC
            LIMIT %(k)s
        """
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_doc(row) for row in rows]


def _rrf_fuse(
    results: Sequence[Tuple[LexicalVariant, Sequence[PgDoc]]],
    *,
    limit: int,
    offset: int,
    k: float = 60.0,
) -> List[PgDoc]:
    if limit <= 0:
        return []
    combined: Dict[str, PgDoc] = {}
    for variant, docs in results:
        for rank, doc in enumerate(docs):
            key = doc.doc_id or doc.id
            if not key:
                continue
            rrf_score = variant.boost * (1.0 / (k + rank + 1))
            if key not in combined:
                combined_doc = replace(doc, score=0.0, score_components=dict(doc.score_components))
                combined[key] = combined_doc
            else:
                combined_doc = combined[key]
            combined_doc.score += rrf_score
            combined_doc.score_components[variant.name] = combined_doc.score_components.get(variant.name, 0.0) + rrf_score
            if doc.score:
                combined_doc.score_components.setdefault(f"raw:{variant.name}", doc.score)
            if doc.snippet and len(doc.snippet) > len(combined_doc.snippet or ""):
                combined_doc.snippet = doc.snippet
            if not combined_doc.body and doc.body:
                combined_doc.body = doc.body
            if not combined_doc.title and doc.title:
                combined_doc.title = doc.title
            if not combined_doc.path and doc.path:
                combined_doc.path = doc.path
    ordered = sorted(combined.values(), key=lambda d: d.score, reverse=True)
    start = max(0, offset)
    end = start + max(0, limit)
    return ordered[start:end]


def search_bm25(query: str, limit: int = 10, offset: int = 0) -> List[PgDoc]:
    dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("PG_DSN")
    if not dsn:
        raise RuntimeError("Set SUPABASE_DB_URL or PG_DSN for Postgres connection.")
    query = (query or "").strip()
    if not query:
        return []

    variants = build_query_variants(query)
    if not variants:
        return []

    psycopg = ensure_psycopg()
    fetch_target = max(limit + offset, 10)
    variant_limit = min(100, max(fetch_target * 2, 25))
    with psycopg.connect(dsn) as conn:
        use_pg_search = _has_extension(conn, "pg_search")
        variant_results: List[Tuple[LexicalVariant, List[PgDoc]]] = []
        for variant in variants:
            rows = _execute_variant(conn, variant, variant_limit, use_pg_search=use_pg_search)
            if rows:
                variant_results.append((variant, rows))
        if not variant_results:
            return []
        fused = _rrf_fuse(variant_results, limit=int(limit), offset=int(max(0, offset)))
    return fused


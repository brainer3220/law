from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Tuple


def ensure_psycopg():
    try:
        import psycopg  # type: ignore
        return psycopg
    except Exception as e:
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


def _has_extension(conn, name: str) -> bool:
    try:
        row = conn.execute("SELECT 1 FROM pg_extension WHERE extname = %s", (name,)).fetchone()
        return bool(row)
    except Exception:
        return False


def search_bm25(query: str, limit: int = 10, offset: int = 0) -> List[PgDoc]:
    dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("PG_DSN")
    if not dsn:
        raise RuntimeError("Set SUPABASE_DB_URL or PG_DSN for Postgres connection.")
    if not query.strip():
        return []

    psycopg = ensure_psycopg()
    with psycopg.connect(dsn) as conn:
        if _has_extension(conn, "pg_search"):
            sql = (
                """
                SELECT id::text,
                       COALESCE(doc_id, ''),
                       COALESCE(title, ''),
                       COALESCE(path, ''),
                       COALESCE(body, ''),
                       paradedb.snippet(body) AS snippet,
                       paradedb.score(id) AS score
                FROM public.legal_docs
                WHERE title @@@ %(q)s OR body @@@ %(q)s
                ORDER BY score DESC
                LIMIT %(k)s OFFSET %(o)s
                """
            )
            rows = conn.execute(sql, {"q": query, "k": int(limit), "o": int(max(0, offset))}).fetchall()
        else:
            # Fallback to PostgreSQL FTS (tsvector + ts_rank)
            sql = (
                """
                WITH cfg AS (
                  SELECT 'simple'::regconfig AS cf
                )
                SELECT id::text,
                       COALESCE(doc_id, ''),
                       COALESCE(title, ''),
                       COALESCE(path, ''),
                       COALESCE(body, ''),
                       ts_headline(cfg.cf, body, plainto_tsquery(cfg.cf, %(q)s)) AS snippet,
                       ts_rank_cd(
                           to_tsvector(cfg.cf, COALESCE(title,'') || ' ' || body),
                           plainto_tsquery(cfg.cf, %(q)s)
                       ) AS score
                FROM public.legal_docs, cfg
                WHERE to_tsvector(cfg.cf, COALESCE(title,'') || ' ' || body) @@ plainto_tsquery(cfg.cf, %(q)s)
                ORDER BY score DESC
                LIMIT %(k)s OFFSET %(o)s
                """
            )
            rows = conn.execute(sql, {"q": query, "k": int(limit), "o": int(max(0, offset))}).fetchall()
    out: List[PgDoc] = []
    for r in rows:
        out.append(
            PgDoc(
                id=r[0],
                doc_id=r[1],
                title=r[2],
                path=r[3],
                body=r[4] or "",
                snippet=r[5] or "",
                score=float(r[6] or 0.0),
            )
        )
    return out

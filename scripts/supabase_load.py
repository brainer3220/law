from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from typing import Iterable

from packages.env import load_env

load_env()


def iter_json_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.json"):
        if p.is_file():
            yield p


def build_title(info: dict) -> str:
    # Prefer explicit title fields, then reasonable fallbacks
    return str(
        info.get("title")
        or info.get("casenames")
        or info.get("caseName")
        or info.get("caseNum")
        or ""
    )


def build_doc_id(info: dict, default: str) -> str:
    return str(
        info.get("doc_id")
        or info.get("precedId")
        or info.get("caseNum")
        or default
    )


def build_body(data: dict) -> str:
    info = data.get("info", {}) or {}
    task = data.get("taskinfo", {}) or {}

    # Case 1: QA-style records with taskinfo (original civil dataset)
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

    # Case 2: Summary-style records (형사법 TL_판결문_SUM)
    # Use fullText as body, add a header line with basic metadata.
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

    # Fallback: dump known info fields into a reasonable body
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


def ensure_psycopg():
    try:
        import psycopg  # type: ignore
        return psycopg
    except Exception as e:
        raise RuntimeError(
            "psycopg is required for Postgres ingest. Install with `uv pip install psycopg[binary]`."
        ) from e


def init_schema(con) -> None:
    with con.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.legal_docs (
              id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              doc_id       text UNIQUE,
              title        text,
              body         text,
              meta         jsonb,
              path         text,
              created_at   timestamptz NOT NULL DEFAULT now()
            );
            """
        )
        bm25_ok = True
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_search;")
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS legal_docs_bm25_idx
                ON public.legal_docs
                USING bm25 (id, title, body)
                WITH (
                  key_field='id',
                  text_fields='{
                    "title": {"tokenizer": {"type": "icu"}},
                    "body":  {"tokenizer": {"type": "icu"}}
                  }'
                );
                """
            )
        except Exception:
            bm25_ok = False
        if not bm25_ok:
            # RUM or GIN fallback
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS rum;")
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS legal_docs_fts_rum
                    ON public.legal_docs
                    USING rum ((to_tsvector('simple', COALESCE(title,'') || ' ' || body))) rum_tsvector_ops;
                    """
                )
            except Exception:
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS legal_docs_fts_gin
                    ON public.legal_docs
                    USING gin (to_tsvector('simple', COALESCE(title,'') || ' ' || body));
                    """
                )


def upsert_rows(con, rows: list[tuple[str, str, str, str, str]]):
    # (doc_id, title, body, meta_json, path)
    sql = (
        """
        INSERT INTO public.legal_docs (doc_id, title, body, meta, path)
        VALUES (%s, %s, %s, %s::jsonb, %s)
        ON CONFLICT (doc_id) DO UPDATE SET
          title = excluded.title,
          body  = excluded.body,
          meta  = excluded.meta,
          path  = excluded.path
        """
    )
    with con.cursor() as cur:
        cur.executemany(sql, rows)


def _normalize_dsn(dsn: str) -> str:
    if "://" in dsn:
        r = urlparse(dsn)
        path = r.path or ""
        if not r.query and "sslmode=" in (path or ""):
            p = path.lstrip("/")
            dbname, _, tail = p.partition("sslmode=")
            dbname = (dbname or "postgres").rstrip("/")
            new_query = "sslmode=" + tail
            r = r._replace(path="/" + dbname, query=new_query)
        q = parse_qs(r.query, keep_blank_values=True)
        if "sslmode" not in q:
            q["sslmode"] = ["require"]
        new_query = urlencode({k: v[-1] if isinstance(v, list) else v for k, v in q.items()}, doseq=True)
        return urlunparse(r._replace(query=new_query))
    return dsn if "sslmode=" in dsn else (dsn + (" " if not dsn.endswith(" ") else "") + "sslmode=require")


def main() -> int:
    dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("PG_DSN")
    if not dsn:
        print("Set SUPABASE_DB_URL or PG_DSN to your Postgres connection string.")
        return 2

    data_dir = Path(os.getenv("LAW_DATA_DIR") or "data")
    if not data_dir.exists():
        print(f"Data directory not found: {data_dir}")
        return 2

    psycopg = ensure_psycopg()
    dsn = _normalize_dsn(dsn)
    with psycopg.connect(dsn) as conn:
        conn.autocommit = True
        conn.execute("SET work_mem = '64MB';")
        init_schema(conn)
        batch: list[tuple[str, str, str, str, str]] = []
        for jp in iter_json_files(data_dir):
            try:
                raw = json.loads(jp.read_text(encoding="utf-8"))
            except Exception:
                continue
            info = raw.get("info", {}) or {}
            task = raw.get("taskinfo", {}) or {}
            doc_id = build_doc_id(info, str(jp))
            title = build_title(info)
            body = build_body(raw)
            meta_json = json.dumps({"info": info, "taskinfo": task}, ensure_ascii=False)
            batch.append((doc_id, title, body, meta_json, str(jp)))
            if len(batch) >= 500:
                upsert_rows(conn, batch)
                batch.clear()
        if batch:
            upsert_rows(conn, batch)
    print("Loaded into Postgres (BM25 indexed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Iterator, Tuple

from law_shared.env import load_env

load_env()


def ensure_psycopg():
    try:
        import psycopg  # type: ignore
        return psycopg
    except Exception as e:
        raise RuntimeError(
            "psycopg is required for Postgres ingest. Install with `uv pip install psycopg[binary]`."
        ) from e


def iter_jsonl_files(path: Path) -> Iterator[Path]:
    if path.is_file() and path.suffix.lower() in {".jsonl", ".ndjson"}:
        yield path
        return
    if path.is_dir():
        for p in sorted(path.rglob("*.jsonl")):
            if p.is_file():
                yield p
        for p in sorted(path.rglob("*.ndjson")):
            if p.is_file():
                yield p


def _normalize_dsn(dsn: str) -> str:
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

    if "://" in dsn:
        r = urlparse(dsn)
        q = parse_qs(r.query, keep_blank_values=True)
        if "sslmode" not in q:
            q["sslmode"] = ["require"]
        new_query = urlencode({k: v[-1] if isinstance(v, list) else v for k, v in q.items()}, doseq=True)
        return urlunparse(r._replace(query=new_query))
    return dsn if "sslmode=" in dsn else (dsn + (" " if not dsn.endswith(" ") else "") + "sslmode=require")


def init_schema(con) -> None:
    # Reuse the same table/indexing strategy as scripts/supabase_load.py
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


def map_case_obj_to_row(obj: dict, source: str, lineno: int) -> tuple[str, str, str, str, str]:
    """Map a case JSON object to (doc_id, title, body, meta_json, path)."""
    doc_id = str(obj.get("id", "")).strip() or f"{source}:{lineno}"
    title = str(obj.get("casename", "")).strip()
    body = str(obj.get("facts", "")).strip()
    meta_json = json.dumps(obj, ensure_ascii=False)
    path = f"{source}:{lineno}"
    return (doc_id, title, body, meta_json, path)


def load_jsonl_into_db(jsonl_path: Path) -> int:
    dsn = os.getenv("SUPABASE_DB_URL") or os.getenv("PG_DSN")
    if not dsn:
        print("Set SUPABASE_DB_URL or PG_DSN to your Postgres connection string.")
        return 2

    psycopg = ensure_psycopg()
    dsn = _normalize_dsn(dsn)
    total = 0
    with psycopg.connect(dsn) as conn:
        conn.autocommit = True
        conn.execute("SET work_mem = '64MB';")
        init_schema(conn)
        batch: list[tuple[str, str, str, str, str]] = []
        for p in iter_jsonl_files(jsonl_path):
            with p.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    row = map_case_obj_to_row(obj, str(p), i)
                    batch.append(row)
                    total += 1
                    if len(batch) >= 1000:
                        upsert_rows(conn, batch)
                        batch.clear()
        if batch:
            upsert_rows(conn, batch)
    print(f"Loaded {total} records from JSONL into Postgres.")
    return 0


def main(jsonl: str | None = None) -> int:
    path_env = jsonl or os.getenv("LAW_JSONL_PATH")
    if not path_env:
        print("Provide path via --jsonl or LAW_JSONL_PATH.")
        return 2
    p = Path(path_env)
    if not p.exists():
        print(f"Path not found: {p}")
        return 2
    return load_jsonl_into_db(p)


if __name__ == "__main__":
    import sys

    jsonl_arg = None
    if len(sys.argv) > 1:
        # allow running directly: python scripts/pg_load_jsonl.py /path/to/file.jsonl
        jsonl_arg = sys.argv[1]
    raise SystemExit(main(jsonl=jsonl_arg))


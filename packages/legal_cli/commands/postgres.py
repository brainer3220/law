"""Postgres/Supabase management commands."""

from __future__ import annotations

import os
from argparse import _SubParsersAction, Namespace
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from ..config import RuntimeConfig

__all__ = ["register"]


def register(subparsers: _SubParsersAction) -> None:
    pg_init = subparsers.add_parser(
        "pg-init", help="Create Supabase/Postgres schema + BM25 index"
    )
    pg_init.set_defaults(handler=_cmd_pg_init)

    pg_load = subparsers.add_parser(
        "pg-load", help="Ingest local JSON into Supabase/Postgres"
    )
    pg_load.add_argument(
        "--data-dir", dest="data_dir", help="Path to data directory (default: ./data)"
    )
    pg_load.set_defaults(handler=_cmd_pg_load)

    pg_load_jsonl = subparsers.add_parser(
        "pg-load-jsonl", help="Ingest NDJSON cases into Supabase/Postgres"
    )
    pg_load_jsonl.add_argument(
        "--jsonl", required=True, help="Path to .jsonl/.ndjson file or directory"
    )
    pg_load_jsonl.set_defaults(handler=_cmd_pg_load_jsonl)

    pg_search = subparsers.add_parser(
        "pg-search", help="Search Supabase/Postgres with BM25"
    )
    pg_search.add_argument("query", help="Keyword to search (BM25)")
    pg_search.add_argument("--limit", type=int, default=10)
    pg_search.add_argument(
        "--full", action="store_true", help="Print full body instead of snippet"
    )
    pg_search.add_argument(
        "--chars",
        type=int,
        default=0,
        help="Limit characters for printed body/snippet (0 for unlimited)",
    )
    pg_search.set_defaults(handler=_cmd_pg_search)


def _pg_require() -> None:
    try:
        import psycopg  # type: ignore  # noqa: F401
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "psycopg is required. Install with `uv pip install psycopg[binary]`."
        ) from exc


def _normalize_dsn(dsn: str) -> str:
    if "://" in dsn:
        parsed = urlparse(dsn)
        path = parsed.path or ""
        if not parsed.query and "sslmode=" in (path or ""):
            tail_path = path.lstrip("/")
            dbname, _, tail = tail_path.partition("sslmode=")
            dbname = (dbname or "postgres").rstrip("/")
            new_query = "sslmode=" + tail
            parsed = parsed._replace(path="/" + dbname, query=new_query)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if "sslmode" not in query:
            query["sslmode"] = ["require"]
        new_query = urlencode(
            {
                key: values[-1] if isinstance(values, list) else values
                for key, values in query.items()
            },
            doseq=True,
        )
        return urlunparse(parsed._replace(query=new_query))
    return (
        dsn
        if "sslmode=" in dsn
        else (dsn + (" " if not dsn.endswith(" ") else "") + "sslmode=require")
    )


def _pg_dsn() -> str:
    raw = os.getenv("SUPABASE_DB_URL") or os.getenv("PG_DSN")
    if not raw:
        raise RuntimeError("Set SUPABASE_DB_URL or PG_DSN for Postgres connection.")
    return _normalize_dsn(raw)


def _cmd_pg_init(_: Namespace, __: RuntimeConfig) -> None:
    _pg_require()
    import psycopg  # type: ignore

    dsn = _pg_dsn()
    sql_path = Path("scripts/sql/supabase_bm25.sql")
    sql = sql_path.read_text(encoding="utf-8") if sql_path.exists() else ""
    if not sql.strip():
        raise RuntimeError("Schema SQL not found: scripts/sql/supabase_bm25.sql")

    try:
        with psycopg.connect(dsn) as conn:  # type: ignore[arg-type]
            conn.autocommit = True
            with conn.cursor() as cur:
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

                if bm25_ok:
                    print("Initialized with pg_search (BM25).")
                    return

                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS rum;")
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS legal_docs_fts_rum
                        ON public.legal_docs
                        USING rum ((to_tsvector('simple', COALESCE(title,'') || ' ' || body))) rum_tsvector_ops;
                        """
                    )
                    print("Initialized with RUM FTS (fallback).")
                    return
                except Exception:
                    pass

                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS legal_docs_fts_gin
                    ON public.legal_docs
                    USING gin (to_tsvector('simple', COALESCE(title,'') || ' ' || body));
                    """
                )
                print("Initialized with GIN FTS (fallback).")
    except Exception as exc:
        message = str(exc)
        if (
            "invalid response to SSL negotiation" in message
            or "server does not support SSL" in message
        ):
            raise RuntimeError(
                "Connection failed during SSL negotiation. Verify host/port and add sslmode=require.\n"
                "- Supabase direct port: 5432 (or pooled: 6543)\n"
                "- Example DSN: postgres://user:pass@host:5432/postgres?sslmode=require"
            ) from exc
        raise


def _cmd_pg_load(args: Namespace, _: RuntimeConfig) -> None:
    from scripts.supabase_load import main as load_main  # type: ignore

    if getattr(args, "data_dir", None):
        os.environ["LAW_DATA_DIR"] = str(Path(args.data_dir))
    rc = load_main()
    if rc != 0:
        raise SystemExit(rc)


def _cmd_pg_load_jsonl(args: Namespace, _: RuntimeConfig) -> None:
    from scripts.pg_load_jsonl import main as load_jsonl_main  # type: ignore

    jsonl = getattr(args, "jsonl", None)
    if not jsonl:
        raise SystemExit("--jsonl path is required")
    rc = load_jsonl_main(jsonl=str(jsonl))
    if rc != 0:
        raise SystemExit(rc)


def _cmd_pg_search(args: Namespace, _: RuntimeConfig) -> None:
    from packages.legal_tools.pg_search import search_bm25  # type: ignore

    rows = search_bm25(args.query, limit=int(args.limit))
    if not rows:
        print("No matches.")
        return
    for index, row in enumerate(rows, start=1):
        snippet = row.snippet
        max_chars = int(getattr(args, "chars", 160) or 0)
        if not getattr(args, "full", False) and max_chars and len(snippet) > max_chars:
            snippet = snippet[: max_chars - 3] + "..."
        print(f"[{index}] {row.title} ({row.doc_id}) score={row.score:.4f}")
        if row.path:
            print(f"    {row.path}")
        if getattr(args, "full", False):
            body = row.body or ""
            if max_chars and len(body) > max_chars:
                body = body[: max_chars - 3] + "..."
            if body:
                print(f"    {body}")
        else:
            if snippet:
                print(f'    "{snippet}"')

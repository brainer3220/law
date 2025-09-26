from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
import logging
import sys
import os
from pathlib import Path
from typing import Iterator, List, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import structlog

from packages.env import load_env

# Ensure `.env` files are processed before reading configuration defaults.
load_env()

# Data directories
DATA_DIR = Path("data")

# Vector/embedding logic removed; keyword search only

 


@dataclass
class Record:
    path: Path
    info: dict
    taskinfo: dict

    @property
    def title(self) -> str:
        return str(self.info.get("title", ""))

    @property
    def doc_id(self) -> str:
        return str(self.info.get("doc_id", ""))

    @property
    def text(self) -> str:
        parts: List[str] = [
            self.doc_id,
            self.title,
            str(self.info.get("response_institute", "")),
            str(self.info.get("response_date", "")),
            str(self.info.get("taskType", "")),
            str(self.taskinfo.get("instruction", "")),
            str(self.taskinfo.get("output", "")),
        ]
        for s in self.taskinfo.get("sentences", []) or []:
            parts.append(str(s))
        return "\n".join(p for p in parts if p)






def iter_json_files(root: Path) -> Iterator[Path]:
    for p in root.rglob("*.json"):
        if p.is_file():
            yield p


def load_record(path: Path) -> Optional[Record]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        info = data.get("info", {}) or {}
        taskinfo = data.get("taskinfo", {}) or {}
        return Record(path=path, info=info, taskinfo=taskinfo)
    except Exception:
        return None


def cmd_preview(args: argparse.Namespace) -> None:
    p = Path(args.path)
    rec = load_record(p)
    if not rec:
        print(f"Failed to load JSON: {p}")
        return
    print(f"Title: {rec.title}")
    print(f"Doc ID: {rec.doc_id}")
    print(f"Institute: {rec.info.get('response_institute', '')}")
    print(f"Date: {rec.info.get('response_date', '')}")
    print(f"TaskType: {rec.info.get('taskType', '')}")
    print("")
    instr = rec.taskinfo.get("instruction", "")
    if instr:
        print("Instruction:")
        print(instr)
        print("")
    sents = rec.taskinfo.get("sentences", []) or []
    if sents:
        print("Sentences (first 3):")
        for s in sents[:3]:
            print("- ", s.strip())
        print("")
    out = rec.taskinfo.get("output", "")
    if out:
        print("Output (truncated):")
        truncated = out if len(out) <= 800 else out[:800] + "..."
        print(truncated)


def cmd_stats(args: argparse.Namespace) -> None:
    total = 0
    institutes = {}
    task_types = {}
    max_title_len = 0
    for path in iter_json_files(DATA_DIR):
        rec = load_record(path)
        if not rec:
            continue
        total += 1
        inst = (rec.info.get("response_institute") or "").strip()
        if inst:
            institutes[inst] = institutes.get(inst, 0) + 1
        tt = (rec.info.get("taskType") or "").strip()
        if tt:
            task_types[tt] = task_types.get(tt, 0) + 1
        max_title_len = max(max_title_len, len(rec.title))

    print(f"Records: {total}")
    if institutes:
        top_inst = sorted(institutes.items(), key=lambda x: x[1], reverse=True)[:5]
        print("Top Institutes:")
        for k, v in top_inst:
            print(f"- {k}: {v}")
    if task_types:
        top_tt = sorted(task_types.items(), key=lambda x: x[1], reverse=True)
        print("Task Types:")
        for k, v in top_tt:
            print(f"- {k}: {v}")
    print(f"Max title length: {max_title_len}")


# =============================
# LangGraph Agent: law ask
# =============================


def cmd_ask(args: argparse.Namespace) -> None:
    try:
        from packages.legal_tools.agent_graph import run_ask  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "LangGraph agent is unavailable. Ensure dependencies are installed with `uv sync`."
        ) from e

    top_k = int(getattr(args, "k", 5))
    allow_general = bool(getattr(args, "flex", False))
    context_chars = int(getattr(args, "context_chars", 0) or 0)
    # Map the previous --max-tool-calls option to LangGraph max_iters
    max_iters = int(getattr(args, "max_tool_calls", 8) or 8)

    # Resolve data directory (CLI flag > env > default ./data)
    data_dir_str = getattr(args, "data_dir", None) or os.getenv("LAW_DATA_DIR") or str(DATA_DIR)
    data_dir = Path(data_dir_str)

    # Offline mode
    if bool(getattr(args, "offline", False)):
        os.environ["LAW_OFFLINE"] = "1"

    result = run_ask(
        args.question,
        data_dir=data_dir,
        top_k=top_k,
        max_iters=max_iters,
        allow_general=allow_general,
        context_chars=context_chars or 800,
    )

    ans = (result.get("answer") or "").strip()
    print(ans if ans else "(LLM 응답이 비어있습니다)")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="law",
        description="MVP CLI to search and preview legal JSON entries.",
    )
    p.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (CRITICAL, ERROR, WARNING, INFO, DEBUG). Default: WARNING",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pp = sub.add_parser("preview", help="Preview a single JSON file")
    pp.add_argument("path", help="Path to JSON file")
    pp.set_defaults(func=cmd_preview)

    st = sub.add_parser("stats", help="Show simple dataset statistics")
    st.set_defaults(func=cmd_stats)

    # Postgres/Supabase BM25 optional commands
    def _pg_require() -> None:
        try:
            import psycopg  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "psycopg is required. Install with `uv pip install psycopg[binary]`."
            ) from e

    def _normalize_dsn(dsn: str) -> str:
        if "://" in dsn:
            r = urlparse(dsn)
            path = r.path or ""
            # Fix cases like .../postgressslmode=require (missing '?')
            if not r.query and "sslmode=" in (path or ""):
                # Take everything after dbname as query
                # e.g., "/postgressslmode=require" -> dbname=postgres, query=sslmode=require
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
        # libpq keyword format: ensure sslmode param
        return dsn if "sslmode=" in dsn else (dsn + (" " if not dsn.endswith(" ") else "") + "sslmode=require")

    def _pg_dsn() -> str:
        raw = os.getenv("SUPABASE_DB_URL") or os.getenv("PG_DSN")
        if not raw:
            raise RuntimeError("Set SUPABASE_DB_URL or PG_DSN for Postgres connection.")
        return _normalize_dsn(raw)

    def _cmd_pg_init(_: argparse.Namespace) -> None:
        _pg_require()
        import psycopg  # type: ignore
        dsn = _pg_dsn()
        sql_path = Path("scripts/sql/supabase_bm25.sql")
        sql = sql_path.read_text(encoding="utf-8") if sql_path.exists() else ""
        if not sql.strip():
            raise RuntimeError("Schema SQL not found: scripts/sql/supabase_bm25.sql")
        try:
            with psycopg.connect(dsn) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    # Base objects
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
                    # Try BM25 (pg_search)
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

                    # Fallback to RUM or GIN FTS
                    rum_ok = True
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
                        rum_ok = False

                    # Final fallback: GIN
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS legal_docs_fts_gin
                        ON public.legal_docs
                        USING gin (to_tsvector('simple', COALESCE(title,'') || ' ' || body));
                        """
                    )
                    print("Initialized with GIN FTS (fallback).")
        except Exception as e:
            msg = str(e)
            if "invalid response to SSL negotiation" in msg or "server does not support SSL" in msg:
                raise RuntimeError(
                    "Connection failed during SSL negotiation. Verify host/port and add sslmode=require.\n"
                    "- Supabase direct port: 5432 (or pooled: 6543)\n"
                    "- Example DSN: postgres://user:pass@host:5432/postgres?sslmode=require"
                ) from e
            raise

    def _cmd_pg_load(a: argparse.Namespace) -> None:
        # Delegate to scripts/supabase_load.py for simplicity
        from scripts.supabase_load import main as load_main  # type: ignore

        if getattr(a, "data_dir", None):
            os.environ["LAW_DATA_DIR"] = str(Path(a.data_dir))
        rc = load_main()
        if rc != 0:
            raise SystemExit(rc)

    def _cmd_pg_search(a: argparse.Namespace) -> None:
        from packages.legal_tools.pg_search import search_bm25  # type: ignore

        rows = search_bm25(a.query, limit=int(a.limit))
        if not rows:
            print("No matches.")
            return
        for i, r in enumerate(rows, start=1):
            snip = r.snippet
            max_chars = int(getattr(a, "chars", 160) or 0)
            if not getattr(a, "full", False):
                if max_chars and len(snip) > max_chars:
                    snip = snip[: max_chars - 3] + "..."
            print(f"[{i}] {r.title} ({r.doc_id}) score={r.score:.4f}")
            if r.path:
                print(f"    {r.path}")
            if getattr(a, "full", False):
                body = r.body or ""
                if max_chars and len(body) > max_chars:
                    body = body[: max_chars - 3] + "..."
                if body:
                    print(f"    {body}")
            else:
                if snip:
                    print(f"    \"{snip}\"")

    pg_init = sub.add_parser("pg-init", help="Create Supabase/Postgres schema + BM25 index")
    pg_init.set_defaults(func=_cmd_pg_init)

    pg_load = sub.add_parser("pg-load", help="Ingest local JSON into Supabase/Postgres")
    pg_load.add_argument("--data-dir", dest="data_dir", help="Path to data directory (default: ./data)")
    pg_load.set_defaults(func=_cmd_pg_load)

    def _cmd_opensearch_load(a: argparse.Namespace) -> None:
        from scripts.opensearch_load import main as opensearch_main  # type: ignore

        rc = opensearch_main(
            data_dir=getattr(a, "data_dir", None), index_name=getattr(a, "index", None)
        )
        if rc != 0:
            raise SystemExit(rc)

    def _cmd_opensearch_search(a: argparse.Namespace) -> None:
        from packages.legal_tools.opensearch_search import search_opensearch  # type: ignore

        docs = search_opensearch(
            a.query,
            limit=int(getattr(a, "limit", 10) or 10),
            offset=int(getattr(a, "offset", 0) or 0),
            index=getattr(a, "index", None),
        )
        if not docs:
            print("No matches.")
            return
        for i, doc in enumerate(docs, start=1):
            snippet = doc.snippet or doc.body or ""
            max_chars = int(getattr(a, "chars", 160) or 0)
            if not getattr(a, "full", False):
                if max_chars and len(snippet) > max_chars:
                    snippet = snippet[: max_chars - 3] + "..."
            print(f"[{i}] {doc.title} ({doc.doc_id or doc.id}) score={doc.score:.4f}")
            if doc.source_path:
                print(f"    {doc.source_path}")
            if getattr(a, "full", False):
                body = doc.body or ""
                if max_chars and len(body) > max_chars:
                    body = body[: max_chars - 3] + "..."
                if body:
                    print(f"    {body}")
            else:
                if snippet:
                    print(f"    \"{snippet}\"")

    opensearch_load = sub.add_parser(
        "opensearch-load", help="Ingest local JSON into OpenSearch"
    )
    opensearch_load.add_argument(
        "--data-dir",
        dest="data_dir",
        help="Path to data directory (default: ./data/opensearch)",
    )
    opensearch_load.add_argument(
        "--index",
        dest="index",
        help="OpenSearch index name (default: legal-docs)",
    )
    opensearch_load.set_defaults(func=_cmd_opensearch_load)

    opensearch_search = sub.add_parser("opensearch-search", help="Search OpenSearch index")
    opensearch_search.add_argument("query", help="Keyword to search")
    opensearch_search.add_argument("--limit", type=int, default=10)
    opensearch_search.add_argument(
        "--offset", type=int, default=0, help="Result offset for pagination"
    )
    opensearch_search.add_argument(
        "--index", dest="index", help="OpenSearch index name (default: env or legal-docs)"
    )
    opensearch_search.add_argument(
        "--full", action="store_true", help="Print full body instead of snippet"
    )
    opensearch_search.add_argument(
        "--chars",
        type=int,
        default=0,
        help="Limit characters for printed body/snippet (0 for unlimited)",
    )
    opensearch_search.set_defaults(func=_cmd_opensearch_search)

    def _cmd_pg_load_jsonl(a: argparse.Namespace) -> None:
        # Load newline-delimited JSON (id, casetype, casename, facts) into legal_docs
        from scripts.pg_load_jsonl import main as load_jsonl_main  # type: ignore

        jsonl = getattr(a, "jsonl", None)
        if not jsonl:
            raise SystemExit("--jsonl path is required")
        rc = load_jsonl_main(jsonl=str(jsonl))
        if rc != 0:
            raise SystemExit(rc)

    pg_load_jsonl = sub.add_parser("pg-load-jsonl", help="Ingest NDJSON cases into Supabase/Postgres")
    pg_load_jsonl.add_argument("--jsonl", required=True, help="Path to .jsonl/.ndjson file or directory")
    pg_load_jsonl.set_defaults(func=_cmd_pg_load_jsonl)

    pg_search = sub.add_parser("pg-search", help="Search Supabase/Postgres with BM25")
    pg_search.add_argument("query", help="Keyword to search (BM25)")
    pg_search.add_argument("--limit", type=int, default=10)
    pg_search.add_argument("--full", action="store_true", help="Print full body instead of snippet")
    pg_search.add_argument(
        "--chars",
        type=int,
        default=0,
        help="Limit characters for printed body/snippet (0 for unlimited)",
    )
    pg_search.set_defaults(func=_cmd_pg_search)

    # LangGraph ask agent
    ask = sub.add_parser("ask", help="Agentic Q&A over local data (ReAct tool-use)")
    ask.add_argument("question", help="Natural language question (ko)")
    ask.add_argument("--k", type=int, default=5, help="Top-k evidence to cite")
    # ReAct mode is default; max-iters is deprecated
    ask.add_argument("--max-tool-calls", type=int, default=8, help="Tool calls budget (ReAct mode)")
    ask.add_argument("--flex", action="store_true", help="Allow general knowledge when evidence is insufficient")
    ask.add_argument(
        "--context-chars",
        type=int,
        default=0,
        help="Include up to N chars of raw body context with each snippet (0 to disable)",
    )
    ask.add_argument("--data-dir", dest="data_dir", help="Path to data directory (default: ./data)")
    ask.add_argument("--offline", action="store_true", help="Disable external LLM calls (offline mode)")
    ask.set_defaults(func=cmd_ask)

    # MCP utilities (optional)
    def _cmd_mcp_context7(a: argparse.Namespace) -> None:
        from packages.legal_tools.mcp_client import context7_docs, MCPUnavailable  # type: ignore

        try:
            out = context7_docs(a.library, topic=getattr(a, "topic", None), tokens=int(getattr(a, "tokens", 5000)))
        except MCPUnavailable as e:
            raise SystemExit(str(e))
        print(out)

    mcp_c7 = sub.add_parser("mcp-context7-docs", help="Fetch docs via Context7 MCP (optional)")
    mcp_c7.add_argument("library", help="Library name to resolve (e.g., 'requests', 'next.js')")
    mcp_c7.add_argument("--topic", help="Optional topic focus", default=None)
    mcp_c7.add_argument("--tokens", type=int, default=5000, help="Max tokens to retrieve")
    mcp_c7.set_defaults(func=_cmd_mcp_context7)

    def _cmd_mcp_ast_grep(a: argparse.Namespace) -> None:
        from packages.legal_tools.mcp_client import ast_grep_find, MCPUnavailable  # type: ignore

        proj = getattr(a, "project", None) or str(Path.cwd())
        try:
            out = ast_grep_find(a.pattern, project_dir=proj, language=getattr(a, "language", None), max_results=int(getattr(a, "max_results", 50)))
        except MCPUnavailable as e:
            raise SystemExit(str(e))
        print(out)

    mcp_ag = sub.add_parser("mcp-ast-grep", help="Search code via ast-grep MCP (optional)")
    mcp_ag.add_argument("pattern", help="Pattern or YAML rule text")
    mcp_ag.add_argument("--project", help="Project root (default: CWD)")
    mcp_ag.add_argument("--language", help="Language hint (e.g., python, typescript)")
    mcp_ag.add_argument("--max-results", type=int, default=50)
    mcp_ag.set_defaults(func=_cmd_mcp_ast_grep)

    # Serve an OpenAI-compatible, streaming Chat Completions API over HTTP
    def _cmd_serve(a: argparse.Namespace) -> None:
        from packages.legal_tools.api_server import serve as api_serve  # type: ignore

        host = getattr(a, "host", "127.0.0.1")
        port = int(getattr(a, "port", 8080))
        # Allow overriding data directory for the agent via env
        if getattr(a, "data_dir", None):
            os.environ["LAW_DATA_DIR"] = str(Path(a.data_dir))
        api_serve(host=host, port=port)

    srv = sub.add_parser("serve", help="Run OpenAI-compatible streaming API server")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8080)
    srv.add_argument("--data-dir", dest="data_dir", help="Path to data directory (default: ./data)")
    srv.set_defaults(func=_cmd_serve)

    return p


def configure_logging(level_name: str) -> None:
    level_value = getattr(logging, level_name.upper(), logging.WARNING)
    timestamper = structlog.processors.TimeStamper(fmt="iso", key="timestamp")

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.KeyValueRenderer(
            key_order=["timestamp", "level", "logger", "event"],
            sort_keys=True,
        ),
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    handler.setLevel(level_value)

    logging.basicConfig(level=level_value, handlers=[handler], force=True)


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Configure logging early
    level_name = str(getattr(args, "log_level", "WARNING")).upper()
    configure_logging(level_name)
    args.func(args)


if __name__ == "__main__":
    main()

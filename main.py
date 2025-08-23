from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "records.duckdb"


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


# =====================
# Supabase/Postgres I/O
# =====================

def _pg_connect(dsn_override: Optional[str] = None):
    try:
        import psycopg  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "psycopg (v3) is required for Supabase/Postgres. Install with `uv add psycopg[binary]` or `uv sync`."
        ) from e

    dsn = dsn_override or os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "Set SUPABASE_DB_URL or DATABASE_URL to your Postgres connection string (service role recommended for ingest)."
        )
    return psycopg.connect(dsn)


def _pg_ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        # Enable useful extensions if allowed
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        except Exception:
            pass

        # Create table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                path TEXT PRIMARY KEY,
                doc_id TEXT,
                title TEXT,
                response_institute TEXT,
                response_date TEXT,
                task_type TEXT,
                instruction TEXT,
                sentences_text TEXT,
                output TEXT,
                full_text TEXT,
                updated_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        # FTS support (generated tsvector). Not all locales may be installed; keep optional.
        try:
            cur.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='records' AND column_name='fts'
                    ) THEN
                        ALTER TABLE records ADD COLUMN fts tsvector GENERATED ALWAYS AS (
                            to_tsvector('simple', coalesce(full_text,''))
                        ) STORED;
                    END IF;
                END$$;
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS records_fts_idx ON records USING GIN (fts)")
        except Exception:
            # Fall back to trigram index on full_text for ILIKE queries
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS records_full_text_trgm ON records USING GIN (full_text gin_trgm_ops)")
            except Exception:
                pass
    conn.commit()


def cmd_ingest_supabase(args: argparse.Namespace) -> None:
    batch_size = int(getattr(args, "batch", 500))
    conn = _pg_connect(getattr(args, "dsn", None))
    _pg_ensure_schema(conn)

    # Collect rows
    rows: List[Tuple[str, str, str, str, str, str, str, str, str, str]] = []
    for path in iter_json_files(DATA_DIR):
        rec = load_record(path)
        if not rec:
            continue
        sentences = rec.taskinfo.get("sentences", []) or []
        sentences_text = " ".join(str(s) for s in sentences if s)
        full_text = " ".join(
            s
            for s in [
                rec.doc_id,
                rec.title,
                str(rec.info.get("response_institute", "")),
                str(rec.info.get("response_date", "")),
                str(rec.info.get("taskType", "")),
                str(rec.taskinfo.get("instruction", "")),
                sentences_text,
                str(rec.taskinfo.get("output", "")),
            ]
            if s
        )
        rows.append(
            (
                str(rec.path),
                rec.doc_id,
                rec.title,
                str(rec.info.get("response_institute", "")),
                str(rec.info.get("response_date", "")),
                str(rec.info.get("taskType", "")),
                str(rec.taskinfo.get("instruction", "")),
                sentences_text,
                str(rec.taskinfo.get("output", "")),
                full_text,
            )
        )

    if not rows:
        print("No JSON files found under data/ to ingest.")
        return

    sql = (
        "INSERT INTO records (path, doc_id, title, response_institute, response_date, task_type, instruction, sentences_text, output, full_text)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        " ON CONFLICT (path) DO UPDATE SET "
        " doc_id=EXCLUDED.doc_id, title=EXCLUDED.title, response_institute=EXCLUDED.response_institute,"
        " response_date=EXCLUDED.response_date, task_type=EXCLUDED.task_type, instruction=EXCLUDED.instruction,"
        " sentences_text=EXCLUDED.sentences_text, output=EXCLUDED.output, full_text=EXCLUDED.full_text, updated_at=now()"
    )

    with conn.cursor() as cur:
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            cur.executemany(sql, chunk)
            print(f"Upserted {i + len(chunk)}/{len(rows)}")
    conn.commit()
    print("Ingest complete.")


def cmd_search_supabase(args: argparse.Namespace) -> None:
    query = args.query
    limit = int(getattr(args, "limit", 10))
    conn = _pg_connect(getattr(args, "dsn", None))
    _pg_ensure_schema(conn)

    rows: List[Tuple[str]] = []
    with conn.cursor() as cur:
        # Prefer FTS if fts column exists
        try:
            cur.execute(
                "SELECT path FROM records WHERE fts @@ websearch_to_tsquery('simple', %s) LIMIT %s",
                (query, limit),
            )
            rows = cur.fetchall()
        except Exception:
            # Fallback to trigram/ILIKE search
            like = f"%{query}%"
            cur.execute(
                "SELECT path FROM records WHERE full_text ILIKE %s LIMIT %s",
                (like, limit),
            )
            rows = cur.fetchall()

    if not rows:
        print("No matches found.")
        return

    # Reuse local snippet logic for consistent display
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for idx, (path_str,) in enumerate(rows, start=1):
        p = Path(path_str)
        rec = load_record(p)
        if not rec:
            continue
        print(f"[{idx}] {rec.title} ({rec.doc_id})")
        print(f"    Path: {rec.path}")
        snippets: List[Tuple[int, str]] = []
        for i, line in enumerate(rec.text.splitlines(), start=1):
            if pattern.search(line):
                snippets.append((i, line.strip()))
                if len(snippets) >= 3:
                    break
        for ln, text in snippets:
            snippet = text if len(text) <= 160 else text[:157] + "..."
            print(f"    L{ln}: {snippet}")
        print()


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


def search_records(
    query: str,
    limit: int = 10,
    root: Path = DATA_DIR,
) -> List[Tuple[Record, List[Tuple[int, str]]]]:
    """Fast search using a persistent DuckDB index.

    Previous implementation scanned JSON via `read_json_auto` on every query,
    which is expensive over many files. This version maintains a small on-disk
    index of the text fields and searches it instead, only re-reading files
    whose modification time changed.
    """
    try:
        import duckdb  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "DuckDB is required for search. Install with `uv sync` or `uv pip install -e .`."
        ) from e

    def ensure_index(con: "duckdb.DuckDBPyConnection") -> None:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                path TEXT PRIMARY KEY,
                doc_id TEXT,
                title TEXT,
                response_institute TEXT,
                response_date TEXT,
                taskType TEXT,
                instruction TEXT,
                sentences_text TEXT,
                output TEXT,
                all_text TEXT,
                mtime DOUBLE
            )
            """
        )

        # Snapshot current files and mtimes
        fs_paths: List[Path] = list(iter_json_files(root))
        fs_meta = {str(p): p.stat().st_mtime for p in fs_paths}

        # Load DB meta
        rows = con.execute("SELECT path, mtime FROM records").fetchall()
        db_meta = {str(path): (mtime if isinstance(mtime, (int, float)) else 0.0) for path, mtime in rows}

        # Determine changes
        to_delete = [p for p in db_meta.keys() if p not in fs_meta]
        to_upsert: List[str] = []
        for p, m in fs_meta.items():
            if p not in db_meta or abs(db_meta[p] - m) > 1e-6:
                to_upsert.append(p)

        if to_delete:
            con.executemany("DELETE FROM records WHERE path = ?", [(p,) for p in to_delete])

        if to_upsert:
            # Build rows in Python to avoid re-parsing via DuckDB JSON each search
            batch = []
            for p in to_upsert:
                rec = load_record(Path(p))
                if not rec:
                    continue
                text = rec.text
                sentences = rec.taskinfo.get("sentences", []) or []
                sentences_text = " ".join(str(s) for s in sentences if s)
                all_text = " ".join(
                    s
                    for s in [
                        rec.doc_id,
                        rec.title,
                        str(rec.info.get("response_institute", "")),
                        str(rec.info.get("response_date", "")),
                        str(rec.info.get("taskType", "")),
                        str(rec.taskinfo.get("instruction", "")),
                        sentences_text,
                        str(rec.taskinfo.get("output", "")),
                    ]
                    if s
                )
                batch.append(
                    (
                        str(rec.path),
                        rec.doc_id,
                        rec.title,
                        str(rec.info.get("response_institute", "")),
                        str(rec.info.get("response_date", "")),
                        str(rec.info.get("taskType", "")),
                        str(rec.taskinfo.get("instruction", "")),
                        sentences_text,
                        str(rec.taskinfo.get("output", "")),
                        all_text.lower(),  # store lowercased for case-insensitive search
                        fs_meta[str(rec.path)],
                    )
                )
            if batch:
                # Upsert by deleting existing rows then inserting
                con.executemany("DELETE FROM records WHERE path = ?", [(row[0],) for row in batch])
                con.executemany(
                    """
                    INSERT INTO records (
                        path, doc_id, title, response_institute, response_date, taskType,
                        instruction, sentences_text, output, all_text, mtime
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    batch,
                )

    # Open a persistent DB; create directory if needed
    root.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    ensure_index(con)

    # Search the index (case-insensitive by querying lowercased text)
    rows = con.execute(
        "SELECT path FROM records WHERE all_text LIKE '%' || ? || '%' LIMIT ?",
        [query.lower(), limit],
    ).fetchall()

    matches: List[Tuple[Record, List[Tuple[int, str]]]] = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for (path_str,) in rows:
        filename = Path(str(path_str))
        rec = load_record(filename)
        if not rec:
            continue
        lines = rec.text.splitlines()
        snippets: List[Tuple[int, str]] = []
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                snippets.append((i, line.strip()))
                if len(snippets) >= 3:
                    break
        matches.append((rec, snippets))

    return matches


def cmd_search(args: argparse.Namespace) -> None:
    if not DATA_DIR.exists():
        print(f"Data directory not found: {DATA_DIR}")
        return
    results = search_records(args.query, limit=args.limit)
    if not results:
        print("No matches found.")
        return
    for idx, (rec, hits) in enumerate(results, start=1):
        print(f"[{idx}] {rec.title} ({rec.doc_id})")
        print(f"    Path: {rec.path}")
        for ln, text in hits:
            snippet = text
            # Truncate long snippets for readability
            if len(snippet) > 160:
                snippet = snippet[:157] + "..."
            print(f"    L{ln}: {snippet}")
        print()


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


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="law",
        description="MVP CLI to search and preview legal JSON entries.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="Search dataset by keyword")
    sp.add_argument("query", help="Keyword to search (case-insensitive)")
    sp.add_argument("--limit", type=int, default=10, help="Max results to show")
    sp.set_defaults(func=cmd_search)

    pp = sub.add_parser("preview", help="Preview a single JSON file")
    pp.add_argument("path", help="Path to JSON file")
    pp.set_defaults(func=cmd_preview)

    st = sub.add_parser("stats", help="Show simple dataset statistics")
    st.set_defaults(func=cmd_stats)

    # Optional: reindex command to force rebuild
    ri = sub.add_parser("reindex", help="Rebuild the search index cache")
    def _cmd_reindex(_: argparse.Namespace) -> None:
        try:
            import duckdb  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "DuckDB is required. Install with `uv sync` or `uv pip install -e .`."
            ) from e
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(DB_PATH))
        # Reuse search path logic by calling search with a no-op query to trigger indexing
        # but perform a forced rebuild by dropping table first.
        con.execute("DROP TABLE IF EXISTS records")
        # Trigger index creation
        from types import SimpleNamespace
        _ = search_records(query="", limit=0)
        print("Reindexed.")
    ri.set_defaults(func=_cmd_reindex)

    # Supabase/Postgres commands
    ing = sub.add_parser("ingest-supabase", help="Ingest JSON records into Supabase/Postgres")
    ing.add_argument("--batch", type=int, default=500, help="Upsert batch size")
    ing.add_argument("--dsn", help="Postgres DSN (overrides env)")
    ing.set_defaults(func=cmd_ingest_supabase)

    ss = sub.add_parser("search-supabase", help="Search via Supabase/Postgres FTS/trigram")
    ss.add_argument("query", help="Keyword to search (websearch syntax if FTS)" )
    ss.add_argument("--limit", type=int, default=10)
    ss.add_argument("--dsn", help="Postgres DSN (overrides env)")
    ss.set_defaults(func=cmd_search_supabase)

    return p


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

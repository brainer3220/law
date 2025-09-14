from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import duckdb

_CON: Optional[duckdb.DuckDBPyConnection] = None
_HAS_FTS = True


def _get_con(*, db_path: Path | str = Path("data/cases.duckdb"), hf_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Create (or reuse) a DuckDB connection with HTTPFS + FTS enabled."""
    global _CON
    if _CON is None:
        dbp = Path(db_path)
        dbp.parent.mkdir(parents=True, exist_ok=True)
        _CON = duckdb.connect(str(dbp))
        if hf_path is None:
            split = os.getenv("LBOX_CASES_SPLIT", "train")
            hf_path = f"hf://datasets/lbox/lbox_open/casename_classification/{split}.jsonl"
        needs_httpfs = str(hf_path).startswith("hf://") or str(hf_path).startswith("http")
        if needs_httpfs:
            try:
                _CON.execute("LOAD httpfs;")
            except Exception:
                pass
        global _HAS_FTS
        try:
            _CON.execute("LOAD fts;")
        except Exception:
            _HAS_FTS = False
        _CON.execute(
            """
            CREATE TABLE IF NOT EXISTS cases AS
            SELECT id, casetype, casename, facts
            FROM read_json_auto(?)
            """,
            [str(hf_path)],
        )
        if _HAS_FTS:
            _CON.execute("PRAGMA create_fts_index('cases', 'id', 'casename', 'facts');")
    return _CON


def search_fts(query: str, *, limit: int = 20, hf_path: str | Path | None = None, db_path: Path | str | None = None) -> List[Dict[str, Any]]:
    """Search the LBOX casename dataset using DuckDB FTS."""
    con = _get_con(db_path=db_path or Path("data/cases.duckdb"), hf_path=hf_path)
    results: List[Dict[str, Any]] = []
    if _HAS_FTS:
        rows = con.execute(
            """
            SELECT id, casetype, casename, facts,
                   fts_main_cases.match_bm25(id, ?) AS score
            FROM cases
            WHERE score IS NOT NULL
            ORDER BY score DESC
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        for doc_id, casetype, casename, facts, score in rows:
            results.append(
                {
                    "doc_id": str(doc_id),
                    "casetype": str(casetype),
                    "casename": str(casename),
                    "facts": str(facts),
                    "score": float(score if score is not None else 0.0),
                }
            )
    else:
        rows = con.execute("SELECT id, casetype, casename, facts FROM cases").fetchall()
        q = query.lower()
        for doc_id, casetype, casename, facts in rows:
            text = f"{casename} {facts}".lower()
            if q in text:
                score = float(text.count(q))
                results.append(
                    {
                        "doc_id": str(doc_id),
                        "casetype": str(casetype),
                        "casename": str(casename),
                        "facts": str(facts),
                        "score": score,
                    }
                )
        results.sort(key=lambda r: -r["score"])
        results = results[:limit]
    return results

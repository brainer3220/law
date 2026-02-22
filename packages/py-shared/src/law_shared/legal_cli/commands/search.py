"""Search command for local file-based SQLite index."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace

from ..config import RuntimeConfig

__all__ = ["register"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("search", help="Search local lawstore index")
    parser.add_argument("query", nargs="?", default="", help="Search query")
    parser.add_argument("--type", dest="source_type", choices=["statute", "interpretation"])
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--agency", default=None)
    parser.add_argument("--status", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    parser.set_defaults(handler=_cmd_search)


def _cmd_search(args: Namespace, config: RuntimeConfig) -> None:
    from law_shared.legal_tools.file_search import search_local_index  # type: ignore

    hits = search_local_index(
        data_dir=config.data_dir,
        query=str(getattr(args, "query", "") or ""),
        limit=int(getattr(args, "limit", 10) or 10),
        offset=int(getattr(args, "offset", 0) or 0),
        source_type=getattr(args, "source_type", None),
        year=getattr(args, "year", None),
        agency=getattr(args, "agency", None),
        status=getattr(args, "status", None),
    )
    if not hits:
        print("No matches.")
        return
    for index, hit in enumerate(hits, start=1):
        print(f"[{index}] {hit.title} ({hit.doc_id}) score={hit.score:.4f}")
        if hit.source_path:
            print(f"    {hit.source_path}")
        if hit.snippet:
            print(f'    "{hit.snippet}"')

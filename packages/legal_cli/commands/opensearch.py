"""OpenSearch ingestion and query commands."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace

from ..config import RuntimeConfig

__all__ = ["register"]


def register(subparsers: _SubParsersAction) -> None:
    opensearch_load = subparsers.add_parser(
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
    opensearch_load.set_defaults(handler=_cmd_opensearch_load)

    opensearch_search = subparsers.add_parser(
        "opensearch-search", help="Search OpenSearch index"
    )
    opensearch_search.add_argument("query", help="Keyword to search")
    opensearch_search.add_argument("--limit", type=int, default=10)
    opensearch_search.add_argument(
        "--offset", type=int, default=0, help="Result offset for pagination"
    )
    opensearch_search.add_argument(
        "--index",
        dest="index",
        help="OpenSearch index name (default: env or legal-docs)",
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
    opensearch_search.set_defaults(handler=_cmd_opensearch_search)


def _cmd_opensearch_load(args: Namespace, _: RuntimeConfig) -> None:
    from scripts.opensearch_load import main as opensearch_main  # type: ignore

    rc = opensearch_main(
        data_dir=getattr(args, "data_dir", None),
        index_name=getattr(args, "index", None),
    )
    if rc != 0:
        raise SystemExit(rc)


def _cmd_opensearch_search(args: Namespace, _: RuntimeConfig) -> None:
    from packages.legal_tools.opensearch_search import search_opensearch  # type: ignore

    docs = search_opensearch(
        args.query,
        limit=int(getattr(args, "limit", 10) or 10),
        offset=int(getattr(args, "offset", 0) or 0),
        index=getattr(args, "index", None),
    )
    if not docs:
        print("No matches.")
        return
    for index, doc in enumerate(docs, start=1):
        snippet = doc.snippet or doc.body or ""
        max_chars = int(getattr(args, "chars", 160) or 0)
        if not getattr(args, "full", False) and max_chars and len(snippet) > max_chars:
            snippet = snippet[: max_chars - 3] + "..."
        print(f"[{index}] {doc.title} ({doc.doc_id or doc.id}) score={doc.score:.4f}")
        if doc.source_path:
            print(f"    {doc.source_path}")
        if getattr(args, "full", False):
            body = doc.body or ""
            if max_chars and len(body) > max_chars:
                body = body[: max_chars - 3] + "..."
            if body:
                print(f"    {body}")
        else:
            if snippet:
                print(f'    "{snippet}"')

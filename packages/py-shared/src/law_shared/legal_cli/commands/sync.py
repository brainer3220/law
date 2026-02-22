"""File-based ingestion commands for law.go.kr datasets."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace

from ..config import RuntimeConfig

__all__ = ["register"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "sync",
        help="Collect statute/interpretation snapshots from law.go.kr into local files",
    )
    parser.add_argument(
        "--type",
        dest="source_type",
        choices=["statute", "interpretation", "all"],
        default="statute",
        help="Source type to sync (default: statute)",
    )
    parser.add_argument("--query", help="Optional query filter", default=None)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--display", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--sleep", dest="sleep_seconds", type=float, default=0.0)
    parser.set_defaults(handler=_cmd_sync)


def _cmd_sync(args: Namespace, config: RuntimeConfig) -> None:
    from law_shared.legal_tools.file_sync import sync_source  # type: ignore

    source_type = str(getattr(args, "source_type", "statute"))
    targets = ["statute", "interpretation"] if source_type == "all" else [source_type]

    for target in targets:
        result = sync_source(
            source_type=target,  # type: ignore[arg-type]
            data_dir=config.data_dir,
            query=getattr(args, "query", None),
            start_page=int(getattr(args, "start_page", 1) or 1),
            max_pages=int(getattr(args, "max_pages", 1) or 1),
            display=int(getattr(args, "display", 100) or 100),
            timeout=float(getattr(args, "timeout", 10.0) or 10.0),
            sleep_seconds=float(getattr(args, "sleep_seconds", 0.0) or 0.0),
        )
        print(
            f"[{target}] scanned={result['scanned_count']} saved={result['saved_count']} "
            f"failed={result['failed_count']} pages={result['pages_scanned']} "
            f"next_page={result['next_page_hint']}"
        )

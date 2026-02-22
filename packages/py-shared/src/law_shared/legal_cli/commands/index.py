"""Commands for normalized file generation and SQLite indexing."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace

from ..config import RuntimeConfig

__all__ = ["register"]


def register(subparsers: _SubParsersAction) -> None:
    normalize_parser = subparsers.add_parser(
        "normalize", help="Normalize raw lawstore snapshots into canonical JSON documents"
    )
    normalize_parser.add_argument(
        "--type",
        dest="source_type",
        choices=["statute", "interpretation"],
        default=None,
        help="Optional source filter",
    )
    normalize_parser.set_defaults(handler=_cmd_normalize)

    index_parser = subparsers.add_parser(
        "index", help="Build or update local SQLite FTS index from normalized documents"
    )
    index_parser.add_argument(
        "action",
        nargs="?",
        default="update",
        choices=["rebuild", "update"],
        help="Index action (default: update)",
    )
    index_parser.set_defaults(handler=_cmd_index)


def _cmd_normalize(args: Namespace, config: RuntimeConfig) -> None:
    from law_shared.legal_tools.file_normalize import normalize_documents  # type: ignore

    result = normalize_documents(
        data_dir=config.data_dir,
        source_type=getattr(args, "source_type", None),
    )
    print(f"normalized scanned={result['scanned']} created={result['created']}")


def _cmd_index(args: Namespace, config: RuntimeConfig) -> None:
    from law_shared.legal_tools.file_index_sqlite import rebuild_index, update_index  # type: ignore

    action = str(getattr(args, "action", "update"))
    if action == "rebuild":
        result = rebuild_index(data_dir=config.data_dir)
    else:
        result = update_index(data_dir=config.data_dir)
    print(f"index {action} indexed={result['indexed']}")

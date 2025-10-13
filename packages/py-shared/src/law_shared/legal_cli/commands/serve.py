"""HTTP server command."""

from __future__ import annotations

import os
from argparse import _SubParsersAction, Namespace
from pathlib import Path

from ..config import RuntimeConfig

__all__ = ["register", "run"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "serve", help="Run OpenAI-compatible streaming API server"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--data-dir", dest="data_dir", help="Path to data directory (default: ./data)"
    )
    parser.set_defaults(handler=run)


def run(args: Namespace, config: RuntimeConfig) -> None:
    from law_shared.legal_tools.api_server import serve as api_serve  # type: ignore

    data_dir = (
        Path(args.data_dir) if getattr(args, "data_dir", None) else config.data_dir
    )

    if data_dir:
        os.environ["LAW_DATA_DIR"] = str(data_dir)

    api_serve(
        host=getattr(args, "host", "127.0.0.1"), port=int(getattr(args, "port", 8080))
    )

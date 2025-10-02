"""Command-line entry point for the law toolkit."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Callable, List, Optional

import structlog

from . import commands
from .config import RuntimeConfig, build_runtime_config, bootstrap

CommandHandler = Callable[[argparse.Namespace, RuntimeConfig], None]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="law-cli",
        description="Command-line tools for the law agent stack.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (CRITICAL, ERROR, WARNING, INFO, DEBUG). Default: INFO",
    )
    parser.add_argument(
        "--data-dir",
        dest="data_dir",
        help="Override the default data directory (env: LAW_DATA_DIR)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    commands.register(subparsers)
    return parser


def configure_logging(level_name: str) -> None:
    level_value = getattr(logging, level_name.upper(), logging.INFO)
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
    bootstrap()
    parser = build_parser()
    args = parser.parse_args(argv)

    level_name = str(getattr(args, "log_level", "INFO")).upper()
    configure_logging(level_name)

    handler: CommandHandler = getattr(args, "handler", None)
    if not callable(handler):
        parser.error("Command handler missing")

    runtime = build_runtime_config(
        log_level=level_name,
        data_dir=getattr(args, "data_dir", None),
    )

    handler(args, runtime)


if __name__ == "__main__":  # pragma: no cover
    main()

"""Runtime configuration helpers shared by CLI and service adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os

from packages.env import load_env
from packages.legal_tools.tracing import configure_langsmith

DEFAULT_DATA_DIR = Path("data")


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved configuration for command handlers."""

    data_dir: Path
    log_level: str
    offline: bool = False


def bootstrap() -> None:
    """Load environment variables and tracing configuration once."""

    load_env()
    configure_langsmith()


def resolve_data_dir(explicit: Optional[str] = None) -> Path:
    """Return the data directory honoring CLI overrides and environment variables."""

    candidate = Path(explicit or os.getenv("LAW_DATA_DIR") or DEFAULT_DATA_DIR)
    return candidate


def build_runtime_config(
    *, log_level: str, offline: bool = False, data_dir: Optional[str] = None
) -> RuntimeConfig:
    """Construct a :class:`RuntimeConfig` object for handlers."""

    directory = resolve_data_dir(data_dir)
    return RuntimeConfig(data_dir=directory, log_level=log_level, offline=offline)

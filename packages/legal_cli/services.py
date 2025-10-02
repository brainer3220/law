"""Shared helpers for CLI commands and Worker adapters."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional


@dataclass
class Record:
    """Representation of a legal dataset entry."""

    path: Path
    info: Dict[str, object]
    taskinfo: Dict[str, object]

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
        for sentence in self.taskinfo.get("sentences", []) or []:
            parts.append(str(sentence))
        return "\n".join(segment for segment in parts if segment)


def iter_json_files(root: Path) -> Iterator[Path]:
    """Yield JSON files from *root* recursively."""

    for path in root.rglob("*.json"):
        if path.is_file():
            yield path


def load_record(path: Path) -> Optional[Record]:
    """Load a :class:`Record` from disk, returning ``None`` on failure."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return None

    info = data.get("info", {}) or {}
    taskinfo = data.get("taskinfo", {}) or {}
    return Record(path=path, info=info, taskinfo=taskinfo)


def enable_offline_mode(flag: bool) -> None:
    """Set environment variable hooks for offline execution."""

    if flag:
        os.environ["LAW_OFFLINE"] = "1"

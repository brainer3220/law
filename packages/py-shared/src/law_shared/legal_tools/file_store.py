from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

LAWSTORE_DIRNAME = "lawstore"
RAW_DIRNAME = "raw"
NORMALIZED_DIRNAME = "normalized"
INDEX_DIRNAME = "index"
MANIFEST_DIRNAME = "manifests"


def lawstore_root(data_dir: Path) -> Path:
    return data_dir / LAWSTORE_DIRNAME


def raw_root(data_dir: Path) -> Path:
    return lawstore_root(data_dir) / RAW_DIRNAME


def normalized_root(data_dir: Path) -> Path:
    return lawstore_root(data_dir) / NORMALIZED_DIRNAME


def index_root(data_dir: Path) -> Path:
    return lawstore_root(data_dir) / INDEX_DIRNAME


def manifests_root(data_dir: Path) -> Path:
    return lawstore_root(data_dir) / MANIFEST_DIRNAME


def ensure_layout(data_dir: Path) -> None:
    raw_root(data_dir).mkdir(parents=True, exist_ok=True)
    normalized_root(data_dir).mkdir(parents=True, exist_ok=True)
    index_root(data_dir).mkdir(parents=True, exist_ok=True)
    manifests_root(data_dir).mkdir(parents=True, exist_ok=True)


def utc_now() -> datetime:
    return datetime.utcnow()


def utc_now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat() + "Z"


def sanitize_token(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "unknown"
    return re.sub(r"[^0-9A-Za-z_.-]+", "-", text)


def build_doc_id(*, source_type: str, source_id: str, version: str) -> str:
    return (
        f"law_go_kr:{sanitize_token(source_type)}:"
        f"{sanitize_token(source_id)}:{sanitize_token(version)}"
    )


def snapshot_path(
    *,
    data_dir: Path,
    source_type: str,
    source_id: str,
    version: str,
    collected_at: datetime,
) -> Path:
    source_segment = sanitize_token(source_type)
    date_dir = collected_at.strftime("%Y/%m/%d")
    filename = f"{sanitize_token(source_id)}_{sanitize_token(version)}.json"
    return raw_root(data_dir) / source_segment / date_dir / filename


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_snapshot(
    *,
    data_dir: Path,
    source_type: str,
    source_id: str,
    version: str,
    payload: Dict[str, Any],
    collected_at: datetime,
) -> Path:
    path = snapshot_path(
        data_dir=data_dir,
        source_type=source_type,
        source_id=source_id,
        version=version,
        collected_at=collected_at,
    )
    write_json(path, payload)
    return path


def sync_state_path(data_dir: Path) -> Path:
    return manifests_root(data_dir) / "sync_state.json"


def failures_path(data_dir: Path) -> Path:
    return manifests_root(data_dir) / "failures.jsonl"


def load_sync_state(data_dir: Path) -> Dict[str, Any]:
    path = sync_state_path(data_dir)
    if not path.exists():
        return {"sources": {}}
    try:
        value = read_json(path)
    except Exception:
        return {"sources": {}}
    if not isinstance(value, dict):
        return {"sources": {}}
    if "sources" not in value or not isinstance(value["sources"], dict):
        value["sources"] = {}
    return value


def save_sync_state(data_dir: Path, state: Dict[str, Any]) -> None:
    write_json(sync_state_path(data_dir), state)


def append_failure(data_dir: Path, payload: Dict[str, Any]) -> None:
    path = failures_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

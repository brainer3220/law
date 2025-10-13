#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional


def _stable_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()  # stable across runs


def _judgment_key(info: Dict) -> str:
    """Stable key for grouping the same 판결문 across files.

    Priority: explicit doc_id. Fallback: sha1(title|date|institute).
    """
    doc_id = str(info.get("doc_id") or "").strip()
    if doc_id:
        return f"doc:{doc_id}"
    title = str(info.get("title") or "").strip()
    date = str(info.get("response_date") or "").strip()
    inst = str(info.get("response_institute") or "").strip()
    key_src = "\u0001".join([title, date, inst])
    return f"hash:{_stable_hash(key_src)[:16]}"


def iter_json_files(root: Path):
    for p in root.rglob("*.json"):
        if p.is_file():
            yield p


def load_json(path: Path) -> Optional[Dict]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def export_hf(root: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    merged: Dict[str, Dict] = {}
    count_files = 0
    for path in iter_json_files(root):
        data = load_json(path)
        if not data:
            continue
        info = data.get("info", {}) or {}
        taskinfo = data.get("taskinfo", {}) or {}
        count_files += 1
        key = _judgment_key(info)
        if key not in merged:
            merged[key] = {
                "id": key,
                "doc_id": str(info.get("doc_id") or "") or None,
                "title": str(info.get("title") or ""),
                "response_institute": info.get("response_institute"),
                "response_date": info.get("response_date"),
                "task_type": info.get("taskType"),
                "source_uri_examples": [],
                "examples": [],
            }
        entry = merged[key]
        # Fill missing top-level fields if they are empty
        if not entry.get("title") and info.get("title"):
            entry["title"] = info.get("title")
        if not entry.get("response_institute") and info.get("response_institute"):
            entry["response_institute"] = info.get("response_institute")
        if not entry.get("response_date") and info.get("response_date"):
            entry["response_date"] = info.get("response_date")
        if not entry.get("task_type") and info.get("taskType"):
            entry["task_type"] = info.get("taskType")

        example = {
            "instruction": taskinfo.get("instruction"),
            "sentences": taskinfo.get("sentences") or [],
            "output": taskinfo.get("output"),
            "path": str(path),
        }
        entry["examples"].append(example)
        entry["source_uri_examples"].append(str(path))

    with out_path.open("w", encoding="utf-8") as f:
        for v in merged.values():
            f.write(json.dumps(v, ensure_ascii=False) + "\n")

    print(f"Exported {len(merged)} merged judgments from {count_files} files → {out_path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export merged judgments to HuggingFace JSONL")
    p.add_argument("--root", default="data", help="Root directory containing JSON files")
    p.add_argument(
        "--out",
        default="data/hf/judgments.jsonl",
        help="Output JSONL path (default: data/hf/judgments.jsonl)",
    )
    return p


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root)
    out_path = Path(args.out)
    export_hf(root, out_path)


if __name__ == "__main__":
    main()


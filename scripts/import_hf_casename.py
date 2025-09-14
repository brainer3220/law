#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict
from urllib.request import Request, urlopen

SPLITS: Dict[str, str] = {
    "train": "casename_classification/train.jsonl",
    "valid": "casename_classification/valid.jsonl",
    "test": "casename_classification/test.jsonl",
    "test2": "casename_classification/test2.jsonl",
}

BASE_URL = "https://huggingface.co/datasets/lbox/lbox_open/resolve/main/"

def _hf_open(path: str):
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    req = Request(BASE_URL + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return urlopen(req)

def export_split(split: str, out_dir: Path) -> int:
    """Download and convert a dataset split to per‑document JSON files.

    Args:
        split: Dataset split name (train, valid, test, test2).
        out_dir: Directory to write the converted JSON files.
    Returns:
        Number of records written.
    """
    path = SPLITS[split]
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with _hf_open(path) as src:
        for line in src:
            row = json.loads(line)
            obj = {
                "info": {
                    "doc_id": str(row.get("id", "")),
                    "title": row.get("casename", ""),
                    "taskType": row.get("casetype", ""),
                },
                "taskinfo": {
                    "sentences": [row["facts"]] if row.get("facts") else [],
                },
            }
            doc_id = obj["info"]["doc_id"] or str(count)
            dst = out_dir / f"{doc_id}.json"
            dst.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")
            count += 1
    return count

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Download lbox casename classification split from HuggingFace and convert to per-document JSON.",
    )
    p.add_argument(
        "--split",
        choices=sorted(SPLITS),
        default="train",
        help="Dataset split to download (default: train)",
    )
    p.add_argument(
        "--out-dir",
        default="data/lbox_casename",
        help="Root directory for converted JSON files (default: data/lbox_casename)",
    )
    return p

def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir) / args.split
    count = export_split(args.split, out_dir)
    print(f"Saved {count} records under {out_dir}")

if __name__ == "__main__":
    main()

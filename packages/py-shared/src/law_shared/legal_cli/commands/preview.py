"""Preview command implementation."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace
from pathlib import Path

from ..config import RuntimeConfig
from ..services import load_record

__all__ = ["register", "run"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("preview", help="Preview a single JSON file")
    parser.add_argument("path", help="Path to JSON file")
    parser.set_defaults(handler=run)


def run(args: Namespace, _: RuntimeConfig) -> None:
    path = Path(args.path)
    record = load_record(path)
    if not record:
        print(f"Failed to load JSON: {path}")
        return

    print(f"Title: {record.title}")
    print(f"Doc ID: {record.doc_id}")
    print(f"Institute: {record.info.get('response_institute', '')}")
    print(f"Date: {record.info.get('response_date', '')}")
    print(f"TaskType: {record.info.get('taskType', '')}")
    print("")

    instruction = record.taskinfo.get("instruction", "")
    if instruction:
        print("Instruction:")
        print(instruction)
        print("")

    sentences = record.taskinfo.get("sentences", []) or []
    if sentences:
        print("Sentences (first 3):")
        for sentence in sentences[:3]:
            print("- ", sentence.strip())
        print("")

    output = record.taskinfo.get("output", "")
    if output:
        print("Output (truncated):")
        truncated = output if len(output) <= 800 else output[:800] + "..."
        print(truncated)

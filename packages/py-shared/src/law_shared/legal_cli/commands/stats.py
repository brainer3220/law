"""Dataset statistics command."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace

from ..config import RuntimeConfig
from ..services import iter_json_files, load_record

__all__ = ["register", "run"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser("stats", help="Show simple dataset statistics")
    parser.set_defaults(handler=run)


def run(_: Namespace, config: RuntimeConfig) -> None:
    total = 0
    institutes: dict[str, int] = {}
    task_types: dict[str, int] = {}
    max_title_len = 0

    for path in iter_json_files(config.data_dir):
        record = load_record(path)
        if not record:
            continue
        total += 1
        inst = (record.info.get("response_institute") or "").strip()
        if inst:
            institutes[inst] = institutes.get(inst, 0) + 1
        task_type = (record.info.get("taskType") or "").strip()
        if task_type:
            task_types[task_type] = task_types.get(task_type, 0) + 1
        max_title_len = max(max_title_len, len(record.title))

    print(f"Records: {total}")
    if institutes:
        top_inst = sorted(institutes.items(), key=lambda item: item[1], reverse=True)[
            :5
        ]
        print("Top Institutes:")
        for name, count in top_inst:
            print(f"- {name}: {count}")
    if task_types:
        top_task_types = sorted(
            task_types.items(), key=lambda item: item[1], reverse=True
        )
        print("Task Types:")
        for name, count in top_task_types:
            print(f"- {name}: {count}")
    print(f"Max title length: {max_title_len}")

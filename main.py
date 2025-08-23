from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple


DATA_DIR = Path("data")


@dataclass
class Record:
    path: Path
    info: dict
    taskinfo: dict

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
        for s in self.taskinfo.get("sentences", []) or []:
            parts.append(str(s))
        return "\n".join(p for p in parts if p)


def iter_json_files(root: Path) -> Iterator[Path]:
    for p in root.rglob("*.json"):
        if p.is_file():
            yield p


def load_record(path: Path) -> Optional[Record]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        info = data.get("info", {}) or {}
        taskinfo = data.get("taskinfo", {}) or {}
        return Record(path=path, info=info, taskinfo=taskinfo)
    except Exception:
        return None


def search_records(
    query: str,
    limit: int = 10,
    root: Path = DATA_DIR,
) -> List[Tuple[Record, List[Tuple[int, str]]]]:
    """Return list of (record, matches) where matches are (line_no, line_text)."""
    results: List[Tuple[Record, List[Tuple[int, str]]]] = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for path in iter_json_files(root):
        rec = load_record(path)
        if not rec:
            continue
        lines = rec.text.splitlines()
        hits: List[Tuple[int, str]] = []
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                hits.append((i, line.strip()))
                if len(hits) >= 3:
                    # keep a few snippets per record
                    break
        if hits:
            results.append((rec, hits))
            if len(results) >= limit:
                break
    return results


def cmd_search(args: argparse.Namespace) -> None:
    if not DATA_DIR.exists():
        print(f"Data directory not found: {DATA_DIR}")
        return
    results = search_records(args.query, limit=args.limit)
    if not results:
        print("No matches found.")
        return
    for idx, (rec, hits) in enumerate(results, start=1):
        print(f"[{idx}] {rec.title} ({rec.doc_id})")
        print(f"    Path: {rec.path}")
        for ln, text in hits:
            snippet = text
            # Truncate long snippets for readability
            if len(snippet) > 160:
                snippet = snippet[:157] + "..."
            print(f"    L{ln}: {snippet}")
        print()


def cmd_preview(args: argparse.Namespace) -> None:
    p = Path(args.path)
    rec = load_record(p)
    if not rec:
        print(f"Failed to load JSON: {p}")
        return
    print(f"Title: {rec.title}")
    print(f"Doc ID: {rec.doc_id}")
    print(f"Institute: {rec.info.get('response_institute', '')}")
    print(f"Date: {rec.info.get('response_date', '')}")
    print(f"TaskType: {rec.info.get('taskType', '')}")
    print("")
    instr = rec.taskinfo.get("instruction", "")
    if instr:
        print("Instruction:")
        print(instr)
        print("")
    sents = rec.taskinfo.get("sentences", []) or []
    if sents:
        print("Sentences (first 3):")
        for s in sents[:3]:
            print("- ", s.strip())
        print("")
    out = rec.taskinfo.get("output", "")
    if out:
        print("Output (truncated):")
        truncated = out if len(out) <= 800 else out[:800] + "..."
        print(truncated)


def cmd_stats(args: argparse.Namespace) -> None:
    total = 0
    institutes = {}
    task_types = {}
    max_title_len = 0
    for path in iter_json_files(DATA_DIR):
        rec = load_record(path)
        if not rec:
            continue
        total += 1
        inst = (rec.info.get("response_institute") or "").strip()
        if inst:
            institutes[inst] = institutes.get(inst, 0) + 1
        tt = (rec.info.get("taskType") or "").strip()
        if tt:
            task_types[tt] = task_types.get(tt, 0) + 1
        max_title_len = max(max_title_len, len(rec.title))

    print(f"Records: {total}")
    if institutes:
        top_inst = sorted(institutes.items(), key=lambda x: x[1], reverse=True)[:5]
        print("Top Institutes:")
        for k, v in top_inst:
            print(f"- {k}: {v}")
    if task_types:
        top_tt = sorted(task_types.items(), key=lambda x: x[1], reverse=True)
        print("Task Types:")
        for k, v in top_tt:
            print(f"- {k}: {v}")
    print(f"Max title length: {max_title_len}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="law",
        description="MVP CLI to search and preview legal JSON entries.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="Search dataset by keyword")
    sp.add_argument("query", help="Keyword to search (case-insensitive)")
    sp.add_argument("--limit", type=int, default=10, help="Max results to show")
    sp.set_defaults(func=cmd_search)

    pp = sub.add_parser("preview", help="Preview a single JSON file")
    pp.add_argument("path", help="Path to JSON file")
    pp.set_defaults(func=cmd_preview)

    st = sub.add_parser("stats", help="Show simple dataset statistics")
    st.set_defaults(func=cmd_stats)

    return p


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()


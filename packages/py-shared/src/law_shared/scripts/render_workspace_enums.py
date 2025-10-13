#!/usr/bin/env python3
"""Render workspace enum definitions for SQL migrations."""

from __future__ import annotations

import argparse
from pathlib import Path

from law_shared.legal_tools.workspace.schema.enums import render_enum_sql

MARKER = "workspace-enums"


def update_file(path: Path, marker: str, replacement: str) -> None:
    start_token = f"-- <{marker}:start>"
    end_token = f"-- <{marker}:end>"

    text = path.read_text(encoding="utf-8")
    if start_token not in text or end_token not in text:
        raise SystemExit(
            f"Unable to locate markers {start_token!r} and {end_token!r} in {path}"
        )

    before, _, remainder = text.partition(start_token)
    _, _, after = remainder.partition(end_token)

    new_text = f"{before}{start_token}\n{replacement}\n{end_token}{after}"
    path.write_text(new_text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        type=Path,
        help=(
            "Path to a SQL file whose enum block should be replaced between "
            f"-- <{MARKER}:start> and -- <{MARKER}:end> markers"
        ),
    )
    args = parser.parse_args()

    sql = "-- Generated via scripts/render_workspace_enums.py; do not edit manually.\n" + render_enum_sql()
    if args.update is None:
        print(sql)
    else:
        update_file(args.update, MARKER, sql)


if __name__ == "__main__":
    main()

"""Research memo command (BRA-23)."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace
from pathlib import Path

from ..config import RuntimeConfig
from ..services import enable_offline_mode

__all__ = ["register", "run"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "research", help="법령·판례 리서치 메모 생성 (사실관계/쟁점/법리/결론/리스크)"
    )
    parser.add_argument("question", help="리서치할 법률 질문 (ko)")
    parser.add_argument("--k", type=int, default=5, help="Top-k evidence to cite")
    parser.add_argument("--max-tool-calls", type=int, default=3, help="Tool call budget")
    parser.add_argument("--data-dir", dest="data_dir", help="Path to data directory")
    parser.add_argument("--offline", action="store_true", help="Disable external LLM calls")
    parser.set_defaults(handler=run)


def run(args: Namespace, config: RuntimeConfig) -> None:
    from law_shared.legal_tools.research_memo import build_research_memo

    data_dir = (
        Path(args.data_dir) if getattr(args, "data_dir", None) else config.data_dir
    )
    enable_offline_mode(bool(getattr(args, "offline", False)))

    memo = build_research_memo(
        args.question,
        data_dir=data_dir,
        top_k=args.k,
        max_iters=args.max_tool_calls,
    )
    print(memo.to_markdown())

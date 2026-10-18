"""Legal document drafting command (BRA-24)."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace
from pathlib import Path

from ..config import RuntimeConfig
from ..services import enable_offline_mode

__all__ = ["register", "run"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "draft", help="법률 서면 초안 작성 (소장/답변서/준비서면/가처분·가압류신청서/법률의견서/보정서)"
    )
    parser.add_argument("doc_type", help="문서 유형 (예: 소장, 답변서, 준비서면)")
    parser.add_argument("overview", help="사건 개요 (ko)")
    parser.add_argument("--instructions", default="", help="추가 작성 지시")
    parser.add_argument("--k", type=int, default=5, help="Top-k evidence to cite")
    parser.add_argument("--max-tool-calls", type=int, default=3, help="Tool call budget")
    parser.add_argument("--data-dir", dest="data_dir", help="Path to data directory")
    parser.add_argument("--offline", action="store_true", help="Disable external LLM calls")
    parser.set_defaults(handler=run)


def run(args: Namespace, config: RuntimeConfig) -> None:
    from law_shared.legal_tools.drafting import DOCUMENT_TYPES, draft_document

    data_dir = (
        Path(args.data_dir) if getattr(args, "data_dir", None) else config.data_dir
    )
    enable_offline_mode(bool(getattr(args, "offline", False)))

    if args.doc_type not in DOCUMENT_TYPES:
        raise SystemExit(
            f"지원하지 않는 문서 유형입니다: {args.doc_type} "
            f"(지원: {', '.join(DOCUMENT_TYPES)})"
        )

    draft = draft_document(
        args.doc_type,
        args.overview,
        instructions=args.instructions,
        data_dir=data_dir,
        top_k=args.k,
        max_iters=args.max_tool_calls,
    )
    print(draft.to_markdown())

"""LangGraph ask command."""

from __future__ import annotations

from argparse import _SubParsersAction, Namespace
from pathlib import Path

from ..config import RuntimeConfig
from ..services import enable_offline_mode

__all__ = ["register", "run"]


def register(subparsers: _SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "ask", help="Agentic Q&A over local data (ReAct tool-use)"
    )
    parser.add_argument("question", help="Natural language question (ko)")
    parser.add_argument("--k", type=int, default=5, help="Top-k evidence to cite")
    parser.add_argument(
        "--max-tool-calls", type=int, default=8, help="Tool calls budget (ReAct mode)"
    )
    parser.add_argument(
        "--flex",
        action="store_true",
        help="Allow general knowledge when evidence is insufficient",
    )
    parser.add_argument(
        "--context-chars",
        type=int,
        default=0,
        help="Include up to N chars of raw body context with each snippet (0 to disable)",
    )
    parser.add_argument(
        "--data-dir", dest="data_dir", help="Path to data directory (default: ./data)"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable external LLM calls (offline mode)",
    )
    parser.set_defaults(handler=run)


def run(args: Namespace, config: RuntimeConfig) -> None:
    try:
        from packages.legal_tools.agent_graph import run_ask  # type: ignore
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "LangGraph agent is unavailable. Ensure dependencies are installed with `uv sync`."
        ) from exc

    data_dir = (
        Path(args.data_dir) if getattr(args, "data_dir", None) else config.data_dir
    )

    enable_offline_mode(bool(getattr(args, "offline", False)))

    result = run_ask(
        args.question,
        data_dir=data_dir,
        top_k=int(getattr(args, "k", 5)),
        max_iters=int(getattr(args, "max_tool_calls", 8) or 8),
        allow_general=bool(getattr(args, "flex", False)),
        context_chars=int(getattr(args, "context_chars", 0) or 0) or 800,
    )

    answer = (result.get("answer") or "").strip()
    print(answer if answer else "(LLM 응답이 비어있습니다)")

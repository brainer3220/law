from __future__ import annotations

import json
import os
import sys
import types
from argparse import Namespace
from pathlib import Path

import pytest

pytest.importorskip("structlog")

from law_shared.legal_cli import config
from law_shared.legal_cli.commands import ask, stats
from law_shared.legal_cli.runner import build_parser


@pytest.fixture(autouse=True)
def clear_offline_env() -> None:
    os.environ.pop("LAW_OFFLINE", None)
    yield
    os.environ.pop("LAW_OFFLINE", None)


def test_parser_registers_known_commands() -> None:
    parser = build_parser()
    subparsers_action = parser._subparsers._group_actions[0]  # type: ignore[attr-defined]
    assert {"preview", "stats", "ask", "serve"}.issubset(
        subparsers_action.choices.keys()
    )


def test_stats_uses_runtime_data_dir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = tmp_path / "dataset"
    data_dir.mkdir()
    sample = {
        "info": {
            "doc_id": "1",
            "title": "Sample",
            "response_institute": "기관",
            "response_date": "2024-01-01",
            "taskType": "질의",
        },
        "taskinfo": {
            "instruction": "질문",
            "output": "답변",
        },
    }
    (data_dir / "doc.json").write_text(json.dumps(sample), encoding="utf-8")
    runtime = config.RuntimeConfig(data_dir=data_dir, log_level="INFO")
    stats.run(Namespace(), runtime)
    captured = capsys.readouterr()
    assert "Records: 1" in captured.out
    assert "기관" in captured.out


def test_ask_command_enables_offline_and_prints_answer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = types.SimpleNamespace()

    def fake_run_ask(question: str, **_: object) -> dict[str, str]:
        assert question == "테스트"
        return {"answer": "응답"}

    module.run_ask = fake_run_ask  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "law_shared.legal_tools.agent_graph", module)

    args = Namespace(
        question="테스트",
        k=5,
        max_tool_calls=8,
        flex=False,
        context_chars=0,
        data_dir=None,
        offline=True,
    )
    runtime = config.RuntimeConfig(data_dir=Path("."), log_level="INFO")

    ask.run(args, runtime)
    captured = capsys.readouterr()
    assert "응답" in captured.out
    assert os.environ.get("LAW_OFFLINE") == "1"

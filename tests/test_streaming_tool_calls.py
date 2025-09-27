from __future__ import annotations

import pytest

pytest.importorskip("langchain")

from packages.legal_tools.api_server import _normalize_tool_calls
from packages.legal_tools.multi_turn_chat import PostgresChatManager


def _make_manager() -> PostgresChatManager:
    return PostgresChatManager.__new__(PostgresChatManager)


def test_normalize_tool_calls_converts_args_to_strings() -> None:
    tool_calls = [
        {"id": "call_1", "name": "multiply", "args": {"a": 3, "b": 12}},
        {
            "tool_call_id": "call_2",
            "function": {"name": "add", "arguments": "{\"a\": 11}"},
        },
    ]

    normalized = _normalize_tool_calls(tool_calls)

    assert normalized == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "multiply", "arguments": "{\"a\": 3, \"b\": 12}"},
        },
        {
            "id": "call_2",
            "type": "function",
            "function": {"name": "add", "arguments": "{\"a\": 11}"},
        },
    ]


def test_prepare_incoming_message_preserves_tool_call_chunks() -> None:
    manager = _make_manager()
    message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"name": "Multiply"}],
        "tool_call_chunks": [{"index": 0, "args": "{\"a\": 1}"}],
    }

    prepared = manager._prepare_incoming_message(message)

    assert prepared["tool_calls"] == message["tool_calls"]
    assert prepared["tool_call_chunks"] == message["tool_call_chunks"]
    assert prepared["role"] == message["role"]
    assert prepared["content"] == message["content"]
    # Ensure no unexpected fields are present or missing
    expected_keys = set(message.keys())
    assert set(prepared.keys()) == expected_keys


def test_message_to_dict_retains_tool_call_chunks() -> None:
    manager = _make_manager()
    message = {
        "role": "assistant",
        "content": "result",
        "tool_calls": [{"name": "Add"}],
        "tool_call_chunks": [{"index": 1, "args": "{\"b\": 2}"}],
    }

    as_dict = manager._message_to_dict(message)

    assert as_dict["tool_calls"] == message["tool_calls"]
    assert as_dict["tool_call_chunks"] == message["tool_call_chunks"]

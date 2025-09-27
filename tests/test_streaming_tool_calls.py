from __future__ import annotations

import json
import io
from dataclasses import dataclass
from typing import Any, Dict

import pytest

pytest.importorskip("langchain")

from packages.legal_tools.api_server import ChatHandler, _normalize_tool_calls
from packages.legal_tools.multi_turn_chat import PostgresChatManager


def _make_manager() -> PostgresChatManager:
    return PostgresChatManager.__new__(PostgresChatManager)


@dataclass
class FakeToolCall:
    name: str
    args: Dict[str, Any]
    id: str = ""
    tool_call_id: str = ""


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


def test_normalize_tool_calls_accepts_tool_call_objects() -> None:
    tool_calls = [FakeToolCall(name="lookup", args={"q": "law"})]

    normalized = _normalize_tool_calls(tool_calls)

    assert len(normalized) == 1
    call = normalized[0]
    assert call["function"]["name"] == "lookup"
    assert json.loads(call["function"]["arguments"]) == {"q": "law"}
    assert call["id"].startswith("call_0000_")


def test_normalize_tool_calls_handles_empty_iterables() -> None:
    assert _normalize_tool_calls([]) == []
    assert _normalize_tool_calls(None) == []


def test_normalize_tool_calls_skips_malformed_entries(caplog: pytest.LogCaptureFixture) -> None:
    normalized = _normalize_tool_calls([object()])

    assert normalized == []
    assert any("Malformed tool call" in message for message in caplog.text.splitlines())


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


def test_message_to_dict_handles_message_objects() -> None:
    manager = _make_manager()

    class DummyMessage:
        def __init__(self) -> None:
            self.type = "assistant"
            self.role = "assistant"
            self.content = "object-result"
            self.tool_calls = [{"name": "Add"}]
            self.tool_call_chunks = [{"index": 2, "args": "{\"c\": 3}"}]
            self.tool_call_id = "call_object"
            self.additional_kwargs = {"foo": "bar"}

    message = DummyMessage()

    as_dict = manager._message_to_dict(message)

    assert as_dict["role"] == "assistant"
    assert as_dict["content"] == "object-result"
    assert as_dict["tool_calls"] == message.tool_calls
    assert as_dict["tool_call_chunks"] == message.tool_call_chunks
    assert as_dict["tool_call_id"] == message.tool_call_id
    assert as_dict["additional_kwargs"] == message.additional_kwargs


def test_stream_answer_emits_tool_call_chunk_events() -> None:
    class DummyHandler:
        def __init__(self) -> None:
            self.wfile = io.BytesIO()
            self.responses = []
            self.headers = []
            self.ended = False

        def send_response(self, code: int) -> None:
            self.responses.append(code)

        def send_header(self, key: str, value: str) -> None:
            self.headers.append((key, value))

        def end_headers(self) -> None:
            self.ended = True

        def _sse_send(self, obj: Dict[str, Any]) -> None:
            payload = json.dumps(obj, ensure_ascii=False)
            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))

    handler = DummyHandler()
    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "multiply", "arguments": "{\"a\": 1, \"b\": 2}"},
        }
    ]
    tool_call_chunks = [
        {
            "index": 0,
            "id": "call_1",
            "type": "function",
            "function": {"name": "multiply", "arguments": "{\"a\": 1"},
        }
    ]

    ChatHandler._stream_answer(  # type: ignore[arg-type]
        handler,
        chat_id="chat-123",
        model="test-model",
        created=1,
        answer="final result",
        tool_calls=tool_calls,
        tool_call_chunks=tool_call_chunks,
    )

    raw = handler.wfile.getvalue().decode("utf-8")
    blocks = [block for block in raw.split("\n\n") if block]
    payloads = []
    done_seen = False
    for block in blocks:
        assert block.startswith("data: ")
        data = block[len("data: ") :]
        if data == "[DONE]":
            done_seen = True
            continue
        payloads.append(json.loads(data))

    assert done_seen, "Streaming response must terminate with [DONE] marker"

    tool_call_deltas = []
    for payload in payloads:
        choices = payload.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        if "tool_calls" in delta:
            tool_call_deltas.append(delta["tool_calls"])

    assert len(tool_call_deltas) >= 2
    chunk_arguments = [
        calls[0]["function"]["arguments"]
        for calls in tool_call_deltas
        if calls and "function" in calls[0]
    ]
    assert "{\"a\": 1" in chunk_arguments

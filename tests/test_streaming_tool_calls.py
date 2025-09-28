from __future__ import annotations

import io
import json
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict, Iterator, List, Optional

import pytest

pytest.importorskip("langchain")

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolCall,
    ToolCallChunk,
)

from packages.legal_tools.api_server import (
    ChatHandler,
    _normalize_tool_call_chunk,
    _normalize_tool_calls,
)
from packages.legal_tools.multi_turn_chat import ChatResponse, PostgresChatManager


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
            "function": {"name": "add", "arguments": '{"a": 11}'},
        },
    ]

    normalized = _normalize_tool_calls(tool_calls)

    assert normalized == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "multiply", "arguments": '{"a": 3, "b": 12}'},
        },
        {
            "id": "call_2",
            "type": "function",
            "function": {"name": "add", "arguments": '{"a": 11}'},
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


def test_normalize_tool_calls_skips_malformed_entries(
    caplog: pytest.LogCaptureFixture,
) -> None:
    normalized = _normalize_tool_calls([object()])

    assert normalized == []
    assert any("Malformed tool call" in message for message in caplog.text.splitlines())


def test_prepare_incoming_message_preserves_tool_call_chunks() -> None:
    manager = _make_manager()
    message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"name": "Multiply"}],
        "tool_call_chunks": [{"index": 0, "args": '{"a": 1}'}],
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
        "tool_call_chunks": [{"index": 1, "args": '{"b": 2}'}],
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
            self.tool_call_chunks = [{"index": 2, "args": '{"c": 3}'}]
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


def test_stream_messages_streams_tool_calls_before_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _make_manager()

    class FakeGraph:
        def __init__(self) -> None:
            self.messages: List[Dict[str, Any]] = []
            self.checkpoint_id = "chk_test"

        def get_state(self, cfg: Dict[str, Any]) -> SimpleNamespace:
            return SimpleNamespace(
                values={"messages": list(self.messages)},
                config={"configurable": {"checkpoint_id": self.checkpoint_id}},
            )

        def update_state(
            self,
            cfg: Dict[str, Any],
            payload: Dict[str, Any],
            *,
            as_node: Optional[str] = None,
        ) -> None:
            for message in payload.get("messages") or []:
                if hasattr(message, "dict"):
                    self.messages.append(message.dict())
                elif isinstance(message, dict):
                    self.messages.append(dict(message))
                else:
                    self.messages.append({"role": "assistant", "content": str(message)})

        def get_state_history(self, cfg: Dict[str, Any]) -> List[Any]:
            return []

    fake_graph = FakeGraph()
    manager._graph = fake_graph  # type: ignore[attr-defined]
    manager._ensure_graph = lambda: fake_graph  # type: ignore[assignment]

    def fake_load_state(cfg: Dict[str, Any]) -> Any:
        snapshot = fake_graph.get_state(cfg)
        messages = [
            manager._message_to_dict(msg) for msg in snapshot.values["messages"]
        ]
        keys = [manager._compare_key(msg) for msg in messages]
        return messages, keys, snapshot

    manager._load_state = fake_load_state  # type: ignore[assignment]
    manager._extract_checkpoint_id = (
        lambda snapshot: snapshot.config["configurable"].get("checkpoint_id")
        if snapshot
        else None
    )

    monkeypatch.setattr(
        "packages.legal_tools.multi_turn_chat.get_langsmith_callbacks",
        lambda: [],
    )

    def fake_messages_from_dict(messages: List[Dict[str, Any]]) -> List[Any]:
        results: List[Any] = []
        for message in messages:
            role = (message.get("role") or message.get("type") or "").lower()
            content = message.get("content", "")
            if role in {"user", "human"}:
                results.append(HumanMessage(content=content))
            else:
                results.append(AIMessage(content=content))
        return results

    monkeypatch.setattr(
        "packages.legal_tools.multi_turn_chat.messages_from_dict",
        fake_messages_from_dict,
    )

    class FakeModel:
        def stream(self, messages: List[Any]) -> Iterator[Any]:
            yield AIMessageChunk(
                content="",
                tool_call_chunks=[
                    ToolCallChunk(
                        name="multiply",
                        args='{"a": 1}',
                        index=0,
                        id="call_1",
                    )
                ],
            )
            yield AIMessageChunk(content="final result")
            yield AIMessage(
                content="final result",
                tool_calls=[
                    ToolCall(name="multiply", args={"a": 1, "b": 2}, id="call_1")
                ],
                tool_call_chunks=[
                    ToolCallChunk(
                        name="multiply",
                        args='{"a": 1, "b": 2}',
                        index=0,
                        id="call_1",
                    )
                ],
            )

    manager._model = FakeModel()  # type: ignore[attr-defined]

    iterator = manager.stream_messages(
        thread_id="thread-1",
        messages=[{"role": "user", "content": "calc"}],
    )

    events: List[Dict[str, Any]] = []
    response: Optional[ChatResponse] = None
    while True:
        try:
            events.append(next(iterator))
        except StopIteration as stop:
            response = stop.value
            break

    assert response is not None
    assert response.response is not None
    tool_chunk_indexes = [
        idx
        for idx, event in enumerate(events)
        if event.get("type") == "tool_call_chunk"
    ]
    content_indexes = [
        idx for idx, event in enumerate(events) if event.get("type") == "content_delta"
    ]
    assert tool_chunk_indexes and content_indexes, (
        "Expected both tool and content events"
    )
    assert tool_chunk_indexes[0] < content_indexes[0], (
        "Tool call delta must precede textual content"
    )
    assert events[tool_chunk_indexes[0]]["payload"][0]["id"] == "call_1"
    assert events[content_indexes[0]]["payload"] == "final result"

    final_payload = response.response
    assert final_payload.get("tool_calls"), "Chat history should record tool calls"
    assert final_payload.get("tool_call_chunks"), (
        "Chat history should record chunk details"
    )
    assert any(msg.get("tool_call_chunks") for msg in fake_graph.messages), (
        "Graph state should persist tool call chunks"
    )


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

        def _collect_tool_usage(
            self,
            *,
            agent_result: Optional[Dict[str, Any]],
            chat_result: Optional[ChatResponse],
        ) -> Optional[Dict[str, Any]]:
            return None

    handler = DummyHandler()
    tool_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "multiply", "arguments": '{"a": 1, "b": 2}'},
        }
    ]
    tool_call_delta = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "multiply",
                                "arguments": '{"a": 1',
                            },
                        }
                    ]
                }
            }
        ]
    }

    def event_iterator() -> Iterator[Dict[str, Any]]:
        yield {"type": "tool_call_chunk", "payload": tool_call_delta}
        yield {"type": "content_delta", "payload": "final result"}
        return ChatResponse(
            thread_id="thread-1",
            messages=[],
            response={
                "role": "assistant",
                "content": "final result",
                "tool_calls": tool_calls,
            },
            checkpoint_id=None,
            invoked=True,
        )

    final_response = ChatHandler._stream_answer(  # type: ignore[arg-type]
        handler,
        chat_id="chat-123",
        model="test-model",
        created=1,
        thread_id="thread-1",
        tool_calls=tool_calls,
        tool_call_chunks=None,
        fallback_answer="",
        event_iterator=event_iterator(),
        agent_result=None,
        chat_result=None,
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

    tool_delta_index: Optional[int] = None
    content_index: Optional[int] = None
    for idx, payload in enumerate(payloads):
        choices = payload.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        if tool_delta_index is None and delta.get("tool_calls"):
            tool_delta_index = idx
        if content_index is None and delta.get("content"):
            content_index = idx

    assert tool_delta_index is not None and content_index is not None
    assert tool_delta_index < content_index, (
        "Tool call chunk must arrive before content"
    )

    final_chunk = payloads[-1]
    assert final_chunk.get("law", {}).get("tool_call_chunks")
    law_chunks = final_chunk["law"]["tool_call_chunks"]
    assert law_chunks[0]["choices"][0]["delta"]["tool_calls"][0]["id"] == "call_1"

    assert isinstance(final_response, ChatResponse)
    assert final_response.response is not None
    assert "tool_call_chunks" not in final_response.response


def test_normalize_tool_call_chunk_flattens_delta_shapes() -> None:
    chunk = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call_42",
                            "type": "function",
                            "function": {"name": "lookup", "arguments": {"q": "law"}},
                        }
                    ]
                }
            }
        ]
    }

    normalized = _normalize_tool_call_chunk(chunk)

    assert len(normalized) == 1
    call = normalized[0]
    assert call["id"] == "call_42"
    assert call["function"]["name"] == "lookup"
    assert call["function"]["arguments"] == '{"q": "law"}'

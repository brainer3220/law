from __future__ import annotations

import os
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from langchain.chat_models import init_chat_model
from langchain_core.messages import (
    AIMessageChunk,
    BaseMessage,
    message_chunk_to_message,
    messages_from_dict,
)
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import MessagesState, StateGraph, START, END

from packages.legal_tools.tracing import get_langsmith_callbacks, trace_run

__all__ = ["PostgresChatConfig", "ChatResponse", "PostgresChatManager"]


@dataclass
class PostgresChatConfig:
    """Configuration for the multi-turn chat graph."""

    db_uri: str
    model_id: str = os.getenv("LAW_CHAT_MODEL", "openai:gpt-4o-mini")
    auto_setup: bool = True

    @classmethod
    def from_env(cls) -> "PostgresChatConfig":
        """Create a configuration from environment variables."""

        db_uri = (
            os.getenv("LAW_CHAT_DB_URL")
            or os.getenv("SUPABASE_DB_URL")
            or os.getenv("DATABASE_URL")
            or os.getenv("PG_DSN")
            or ""
        )
        if not db_uri:
            raise RuntimeError(
                "Set LAW_CHAT_DB_URL, DATABASE_URL, or PG_DSN to enable Postgres persistence."
            )
        model_id = os.getenv("LAW_CHAT_MODEL", "openai:gpt-4o-mini")
        return cls(db_uri=db_uri, model_id=model_id)


@dataclass
class ChatResponse:
    """Result of a multi-turn chat invocation."""

    thread_id: str
    messages: List[Dict[str, Any]]
    response: Optional[Dict[str, Any]]
    checkpoint_id: Optional[str]
    invoked: bool

    def last_text(self) -> str:
        """Return the assistant text response, if any."""

        if not self.response:
            return ""
        content = self.response.get("content")
        return content if isinstance(content, str) else str(content or "")


class PostgresChatManager:
    """Stateful chat graph backed by a PostgreSQL checkpointer."""

    def __init__(self, *, config: PostgresChatConfig):
        self.config = config
        self._model = init_chat_model(config.model_id)
        self._checkpointer_cm: Optional[AbstractContextManager[PostgresSaver]] = None
        self._checkpointer: Optional[PostgresSaver] = None
        self._graph: Any = None
        try:
            self._checkpointer_cm = PostgresSaver.from_conn_string(config.db_uri)
            self._checkpointer = self._checkpointer_cm.__enter__()
            if config.auto_setup and self._checkpointer is not None:
                self._checkpointer.setup()
            builder = StateGraph(MessagesState)
            builder.add_node("chat_model", self._call_model)
            builder.add_edge(START, "chat_model")
            builder.add_edge("chat_model", END)
            self._graph = builder.compile(checkpointer=self._checkpointer)
        except Exception:
            try:
                self.close()
            except Exception:
                pass
            raise

    # ----------------------------- public API -----------------------------
    def send_messages(
        self, *, thread_id: str, messages: Sequence[Dict[str, Any]]
    ) -> ChatResponse:
        """Append messages to a thread and return the assistant reply."""

        tid = self._normalize_thread_id(thread_id)
        cfg = {"configurable": {"thread_id": tid}}
        incoming = [self._prepare_incoming_message(m) for m in messages if m]
        if not incoming:
            raise ValueError("No messages supplied for invocation.")
        existing, existing_keys, _ = self._load_state(cfg)
        incoming_keys = [self._compare_key(m) for m in incoming]
        shared = self._shared_prefix(existing_keys, incoming_keys)
        new_payloads = incoming[shared:]
        invoked = bool(new_payloads)
        callbacks = list(get_langsmith_callbacks())
        graph_config = dict(cfg)
        if callbacks:
            graph_config = {**cfg, "callbacks": callbacks}
        metadata = {
            "thread_id": tid,
            "incoming_count": len(incoming),
            "new_payloads": len(new_payloads),
            "shared_prefix": shared,
            "invoked": invoked,
        }
        with trace_run("law.chat.send_messages", metadata=metadata):
            if invoked:
                self._ensure_graph().invoke({"messages": new_payloads}, graph_config)
            updated, _, snapshot = self._load_state(cfg)
            response = self._last_assistant(updated)
            checkpoint_id = self._extract_checkpoint_id(snapshot)
            metadata["checkpoint_id"] = checkpoint_id
            metadata["response_available"] = bool(response)
        return ChatResponse(
            thread_id=tid,
            messages=updated,
            response=response,
            checkpoint_id=checkpoint_id,
            invoked=invoked,
        )

    def stream_messages(
        self, *, thread_id: str, messages: Sequence[Dict[str, Any]]
    ) -> Iterator[Dict[str, Any]]:
        """Stream assistant deltas for appended messages.

        The returned iterator yields structured events (content deltas, tool call
        chunks, and full message payloads) and ultimately returns a ``ChatResponse``
        matching :meth:`send_messages` via ``StopIteration.value``.
        """

        tid = self._normalize_thread_id(thread_id)
        cfg = {"configurable": {"thread_id": tid}}
        incoming = [self._prepare_incoming_message(m) for m in messages if m]
        if not incoming:
            raise ValueError("No messages supplied for invocation.")
        existing, existing_keys, _ = self._load_state(cfg)
        incoming_keys = [self._compare_key(m) for m in incoming]
        shared = self._shared_prefix(existing_keys, incoming_keys)
        new_payloads = incoming[shared:]
        invoked = bool(new_payloads)
        callbacks = list(get_langsmith_callbacks())
        graph_config: Dict[str, Any] = dict(cfg)
        if callbacks:
            graph_config = {**cfg, "callbacks": callbacks}
        metadata = {
            "thread_id": tid,
            "incoming_count": len(incoming),
            "new_payloads": len(new_payloads),
            "shared_prefix": shared,
            "invoked": invoked,
        }

        def _unpack_stream_item(event: Any) -> Tuple[Any, Optional[Dict[str, Any]]]:
            if isinstance(event, tuple) and len(event) == 2:
                return event[0], event[1]
            if isinstance(event, dict) and "payload" in event and "metadata" in event:
                return event["payload"], event.get("metadata")
            return event, None

        def _content_from_chunk(chunk: AIMessageChunk) -> str:
            try:
                return self._coerce_content(chunk.content)
            except Exception:
                return str(chunk.content or "")

        def _emit_events() -> Iterator[Dict[str, Any]]:
            with trace_run("law.chat.stream_messages", metadata=metadata):
                if not invoked:
                    updated, _, snapshot = self._load_state(cfg)
                    response = self._last_assistant(updated)
                    checkpoint_id = self._extract_checkpoint_id(snapshot)
                    metadata["checkpoint_id"] = checkpoint_id
                    metadata["response_available"] = bool(response)
                    return ChatResponse(
                        thread_id=tid,
                        messages=updated,
                        response=response,
                        checkpoint_id=checkpoint_id,
                        invoked=invoked,
                    )

                graph = self._ensure_graph()
                stream_fn = getattr(graph, "stream", None)
                using_graph_stream = callable(stream_fn)
                aggregated_chunk: Optional[AIMessageChunk] = None
                aggregated_message: Optional[BaseMessage] = None

                iterator: Optional[Iterator[Any]] = None
                if using_graph_stream:
                    try:
                        iterator = stream_fn(
                            {"messages": new_payloads},
                            graph_config,
                            stream_mode="messages",
                        )
                    except TypeError:
                        iterator = stream_fn({"messages": new_payloads}, graph_config)
                if iterator is None:
                    using_graph_stream = False
                    history_objects = messages_from_dict(existing)
                    incoming_objects = messages_from_dict(new_payloads)
                    if incoming_objects:
                        graph.update_state(
                            cfg, {"messages": incoming_objects}, as_node=START
                        )
                    iterator = self._model.stream(history_objects + incoming_objects)

                try:
                    for raw in iterator:
                        payload, info = _unpack_stream_item(raw)
                        event_metadata = {"metadata": info} if info else {}
                        if isinstance(payload, AIMessageChunk):
                            aggregated_chunk = (
                                payload
                                if aggregated_chunk is None
                                else aggregated_chunk + payload
                            )
                            text_delta = _content_from_chunk(payload)
                            if text_delta:
                                yield {
                                    "type": "content_delta",
                                    "payload": text_delta,
                                    **event_metadata,
                                }
                            tool_chunks = getattr(payload, "tool_call_chunks", None)
                            if tool_chunks:
                                yield {
                                    "type": "tool_call_chunk",
                                    "payload": list(tool_chunks),
                                    **event_metadata,
                                }
                        elif isinstance(payload, BaseMessage):
                            aggregated_message = payload
                            yield {
                                "type": "message",
                                "payload": self._message_to_dict(payload),
                                **event_metadata,
                            }
                        else:
                            yield {"type": "raw", "payload": payload, **event_metadata}
                finally:
                    if not using_graph_stream:
                        final_message: Optional[BaseMessage] = aggregated_message
                        if final_message is None and aggregated_chunk is not None:
                            final_message = message_chunk_to_message(aggregated_chunk)
                        if final_message is not None:
                            graph.update_state(
                                cfg,
                                {"messages": [final_message]},
                                as_node="chat_model",
                            )

                    updated, _, snapshot = self._load_state(cfg)
                    response = self._last_assistant(updated)
                    checkpoint_id = self._extract_checkpoint_id(snapshot)
                    metadata["checkpoint_id"] = checkpoint_id
                    metadata["response_available"] = bool(response)

                return ChatResponse(
                    thread_id=tid,
                    messages=updated,
                    response=response,
                    checkpoint_id=metadata.get("checkpoint_id"),
                    invoked=invoked,
                )

        return _emit_events()

    def get_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Return the current message state for a thread."""

        cfg = {"configurable": {"thread_id": self._normalize_thread_id(thread_id)}}
        messages, _, _ = self._load_state(cfg)
        return messages

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Return the checkpoint history for a thread (latest first)."""

        cfg = {"configurable": {"thread_id": self._normalize_thread_id(thread_id)}}
        history = []
        for snap in self._ensure_graph().get_state_history(cfg):
            messages = [
                self._message_to_dict(m) for m in snap.values.get("messages", [])
            ]
            history.append(
                {
                    "checkpoint_id": self._extract_checkpoint_id(snap),
                    "messages": messages,
                }
            )
        return history

    def new_thread_id(self, *, prefix: str = "thread") -> str:
        """Generate a unique thread identifier."""

        token = uuid.uuid4().hex
        return f"{prefix}-{token}"

    def close(self) -> None:
        """Release the underlying Postgres connection."""

        cm = self._checkpointer_cm
        entered = self._checkpointer is not None
        self._checkpointer_cm = None
        self._checkpointer = None
        if cm is not None and entered:
            cm.__exit__(None, None, None)

    def __enter__(self) -> "PostgresChatManager":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    # --------------------------- internal helpers -------------------------
    def _ensure_graph(self) -> Any:
        if self._graph is None:
            raise RuntimeError("Chat graph is not initialized.")
        return self._graph

    def _call_model(
        self, state: MessagesState, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        response = self._model.invoke(state["messages"])
        return {"messages": [response]}

    def _load_state(
        self, cfg: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]], Optional[Any]]:
        snapshot = self._ensure_graph().get_state(cfg)
        if snapshot is None:
            return [], [], None
        raw = snapshot.values.get("messages", [])
        messages = [self._message_to_dict(msg) for msg in raw]
        keys = [self._compare_key(msg) for msg in messages]
        return messages, keys, snapshot

    def _extract_checkpoint_id(self, snapshot: Optional[Any]) -> Optional[str]:
        if snapshot is None:
            return None
        config = snapshot.config or {}
        configurable = config.get("configurable") or {}
        return configurable.get("checkpoint_id")

    def _prepare_incoming_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        role = self._normalize_role(message.get("role") or message.get("type"))
        content = self._coerce_content(message.get("content"))
        payload: Dict[str, Any] = {"role": role, "content": content}
        for key in (
            "name",
            "tool_calls",
            "tool_call_chunks",
            "tool_call_id",
            "function_call",
        ):
            if key in message:
                payload[key] = message[key]
        if "metadata" in message:
            payload.setdefault("additional_kwargs", {})
            payload["additional_kwargs"].update(dict(message["metadata"]))
        return payload

    def _message_to_dict(self, message: Any) -> Dict[str, Any]:
        if isinstance(message, BaseMessage) or self._looks_like_message_object(message):
            return self._message_from_object(message)
        if isinstance(message, dict):
            return self._message_from_mapping(message)
        return {
            "role": "assistant",
            "content": self._coerce_content(message),
        }

    def _message_from_object(self, message: Any) -> Dict[str, Any]:
        role_attr = getattr(message, "role", None) or getattr(message, "type", None)
        role = self._normalize_role(role_attr)
        content = self._coerce_content(getattr(message, "content", ""))
        data: Dict[str, Any] = {"role": role, "content": content}
        self._copy_optional_fields(
            data,
            message,
            (
                "name",
                "tool_calls",
                "tool_call_chunks",
                "tool_call_id",
            ),
            getter=lambda src, key: getattr(src, key, None),
        )
        extras = getattr(message, "additional_kwargs", None)
        if extras:
            data["additional_kwargs"] = dict(extras)
        return data

    def _message_from_mapping(self, message: Dict[str, Any]) -> Dict[str, Any]:
        role = self._normalize_role(message.get("role") or message.get("type"))
        content = self._coerce_content(message.get("content"))
        data: Dict[str, Any] = {"role": role, "content": content}
        self._copy_optional_fields(
            data,
            message,
            (
                "additional_kwargs",
                "metadata",
                "name",
                "tool_calls",
                "tool_call_chunks",
                "tool_call_id",
            ),
            getter=lambda src, key: src.get(key),
        )
        return data

    @staticmethod
    def _looks_like_message_object(message: Any) -> bool:
        return hasattr(message, "content") and (
            hasattr(message, "role") or hasattr(message, "type")
        )

    @staticmethod
    def _copy_optional_fields(
        target: Dict[str, Any],
        source: Any,
        keys: Iterable[str],
        *,
        getter,
    ) -> None:
        for key in keys:
            value = getter(source, key)
            if value is not None:
                target[key] = value

    def _compare_key(self, message: Dict[str, Any]) -> Tuple[str, str]:
        role = self._normalize_role(message.get("role"))
        content = self._coerce_content(message.get("content"))
        return role, content.strip()

    def _shared_prefix(
        self,
        existing: Sequence[Tuple[str, str]],
        incoming: Sequence[Tuple[str, str]],
    ) -> int:
        count = 0
        for old, new in zip(existing, incoming):
            if old != new:
                break
            count += 1
        return count

    def _last_assistant(
        self, messages: Iterable[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        return next(
            (
                msg
                for msg in reversed(list(messages))
                if self._normalize_role(msg.get("role")) == "assistant"
            ),
            None,
        )

    def _normalize_thread_id(self, thread_id: str) -> str:
        tid = str(thread_id or "").strip()
        if not tid:
            raise ValueError("thread_id must be a non-empty string.")
        if len(tid) > 200:
            raise ValueError("thread_id is too long (max 200 characters).")
        if " " in tid:
            raise ValueError("thread_id cannot contain space characters.")
        return tid

    def _normalize_role(self, role: Optional[str]) -> str:
        value = (role or "").strip().lower()
        if value in {"ai", "assistant"}:
            return "assistant"
        if value in {"human", "user"}:
            return "user"
        if value == "system":
            return "system"
        return "tool" if value == "tool" else value or "assistant"

    def _coerce_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                elif (
                    isinstance(item, dict)
                    and "text" not in item
                    and item.get("type") == "text"
                ):
                    parts.append(str(item.get("text", "")))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

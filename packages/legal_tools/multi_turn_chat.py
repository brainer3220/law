from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import MessagesState, StateGraph, START, END

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
        if isinstance(content, str):
            return content
        return str(content or "")


class PostgresChatManager:
    """Stateful chat graph backed by a PostgreSQL checkpointer."""

    def __init__(self, *, config: PostgresChatConfig):
        self.config = config
        self._model = init_chat_model(config.model_id)
        self._checkpointer = PostgresSaver.from_conn_string(config.db_uri)
        if config.auto_setup:
            self._checkpointer.setup()
        builder = StateGraph(MessagesState)
        builder.add_node("chat_model", self._call_model)
        builder.add_edge(START, "chat_model")
        builder.add_edge("chat_model", END)
        self._graph = builder.compile(checkpointer=self._checkpointer)

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
        if invoked:
            self._graph.invoke({"messages": new_payloads}, cfg)
        updated, _, snapshot = self._load_state(cfg)
        response = self._last_assistant(updated)
        checkpoint_id = self._extract_checkpoint_id(snapshot)
        return ChatResponse(
            thread_id=tid,
            messages=updated,
            response=response,
            checkpoint_id=checkpoint_id,
            invoked=invoked,
        )

    def get_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Return the current message state for a thread."""

        cfg = {"configurable": {"thread_id": self._normalize_thread_id(thread_id)}}
        messages, _, _ = self._load_state(cfg)
        return messages

    def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Return the checkpoint history for a thread (latest first)."""

        cfg = {"configurable": {"thread_id": self._normalize_thread_id(thread_id)}}
        history = []
        for snap in self._graph.get_state_history(cfg):
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

    # --------------------------- internal helpers -------------------------
    def _call_model(
        self, state: MessagesState, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        response = self._model.invoke(state["messages"])
        return {"messages": [response]}

    def _load_state(
        self, cfg: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]], Optional[Any]]:
        snapshot = self._graph.get_state(cfg)
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
        for key in ("name", "tool_calls", "tool_call_id", "function_call"):
            if key in message:
                payload[key] = message[key]
        if "metadata" in message:
            payload.setdefault("additional_kwargs", {})
            payload["additional_kwargs"].update(dict(message["metadata"]))
        return payload

    def _message_to_dict(self, message: Any) -> Dict[str, Any]:
        if isinstance(message, BaseMessage):
            role = self._normalize_role(getattr(message, "role", None) or message.type)
            content = self._coerce_content(getattr(message, "content", ""))
            data: Dict[str, Any] = {"role": role, "content": content}
            if extra := getattr(message, "additional_kwargs", None):
                data["additional_kwargs"] = dict(extra)
            return data
        if isinstance(message, dict):
            role = self._normalize_role(message.get("role") or message.get("type"))
            content = self._coerce_content(message.get("content"))
            data = {"role": role, "content": content}
            for key in (
                "additional_kwargs",
                "metadata",
                "name",
                "tool_calls",
                "tool_call_id",
            ):
                if key in message:
                    data[key] = message[key]
            return data
        return {
            "role": "assistant",
            "content": self._coerce_content(message),
        }

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
        for msg in reversed(list(messages)):
            if self._normalize_role(msg.get("role")) == "assistant":
                return msg
        return None

    def _normalize_thread_id(self, thread_id: str) -> str:
        tid = str(thread_id or "").strip()
        if not tid:
            raise ValueError("thread_id must be a non-empty string.")
        if len(tid) > 200:
            raise ValueError("thread_id is too long (max 200 characters).")
        if ' ' in tid:
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
        if value == "tool":
            return "tool"
        return value or "assistant"

    def _coerce_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        parts.append(str(item["text"]))
                    elif item.get("type") == "text":
                        parts.append(str(item.get("text", "")))
                    else:
                        parts.append(str(item))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)

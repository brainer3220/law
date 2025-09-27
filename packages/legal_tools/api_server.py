from __future__ import annotations

import json
import logging
import os
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from packages.legal_tools.agent_graph import run_ask
from packages.legal_tools.tracing import configure_langsmith, trace_run

try:  # Optional dependency guard for multi-turn chat support
    from packages.legal_tools.multi_turn_chat import (
        ChatResponse,
        PostgresChatConfig,
        PostgresChatManager,
    )
except Exception:  # pragma: no cover - keep server usable without LangGraph deps
    PostgresChatConfig = None  # type: ignore[assignment]
    PostgresChatManager = None  # type: ignore[assignment]
    ChatResponse = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


_CHAT_MANAGER: Optional[PostgresChatManager] = None
_CHAT_MANAGER_ERROR: Optional[str] = None


class _ToolUsageAggregator:
    """Accumulate tool usage deltas for streaming updates."""

    def __init__(self) -> None:
        self._actions: List[Dict[str, Any]] = []
        self._queries: List[str] = []
        self._iterations: Optional[int] = None
        self._error: Optional[str] = None
        self._tool_calls: List[Dict[str, Any]] = []

    def update_event(self, event: str, payload: Dict[str, Any]) -> bool:
        changed = False
        if event == "query":
            query = str(payload.get("query") or "").strip()
            if query and query not in self._queries:
                self._queries.append(query)
                changed = True
        elif event == "action":
            tool = str(payload.get("tool") or "").strip()
            if tool:
                entry: Dict[str, Any] = {"tool": tool}
                raw_payload = payload.get("payload")
                if isinstance(raw_payload, dict):
                    entry["payload"] = dict(raw_payload)
                elif raw_payload is not None:
                    entry["payload"] = raw_payload
                self._actions.append(entry)
                changed = True
        return changed

    def apply_final(self, usage: Optional[Dict[str, Any]]) -> bool:
        changed = False
        if not usage:
            return changed

        actions = usage.get("actions")
        if isinstance(actions, list):
            normalized_actions: List[Dict[str, Any]] = []
            for action in actions:
                if not isinstance(action, dict):
                    continue
                tool = str(action.get("tool") or "").strip()
                if not tool:
                    continue
                entry: Dict[str, Any] = {"tool": tool}
                payload = action.get("payload")
                if isinstance(payload, dict):
                    entry["payload"] = dict(payload)
                elif payload is not None:
                    entry["payload"] = payload
                normalized_actions.append(entry)
            if normalized_actions != self._actions:
                self._actions = normalized_actions
                changed = True
        queries = usage.get("queries")
        if isinstance(queries, list):
            normalized_queries = [
                str(item).strip() for item in queries if str(item or "").strip()
            ]
            if normalized_queries != self._queries:
                self._queries = normalized_queries
                changed = True
        iterations = usage.get("iterations")
        if iterations is not None or self._iterations is not None:
            if isinstance(iterations, int):
                if iterations != self._iterations:
                    self._iterations = iterations
                    changed = True
            elif self._iterations is not None:
                self._iterations = None
                changed = True
        error = usage.get("error")
        if error is not None or self._error is not None:
            error_text = str(error) if error is not None else None
            if error_text != self._error:
                self._error = error_text
                changed = True
        tool_calls = usage.get("tool_calls")
        if isinstance(tool_calls, list) or (
            tool_calls is None and self._tool_calls
        ):
            normalized_calls: List[Dict[str, Any]] = []
            if isinstance(tool_calls, list):
                for call in tool_calls:
                    if isinstance(call, dict):
                        normalized_calls.append(dict(call))
            if normalized_calls != self._tool_calls:
                self._tool_calls = normalized_calls
                changed = True
            elif not normalized_calls and self._tool_calls:
                self._tool_calls = []
                changed = True
        return changed

    def snapshot(self) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {}
        if self._actions:
            payload["actions"] = [dict(action) for action in self._actions]
        if self._queries:
            payload["queries"] = list(self._queries)
        if self._iterations is not None:
            payload["iterations"] = self._iterations
        if self._error:
            payload["error"] = self._error
        if self._tool_calls:
            payload["tool_calls"] = [dict(call) for call in self._tool_calls]
        return payload or None


def _extract_question(messages: List[Dict[str, Any]]) -> str:
    """Extract the latest user message content as the question."""
    if not messages:
        return ""
    question = ""
    for m in messages:
        if str(m.get("role", "")).lower() == "user":
            question = str(m.get("content", ""))
    return question


def _json_response(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _get_chat_manager() -> Optional[PostgresChatManager]:
    """Lazily initialize the Postgres-backed chat manager."""

    global _CHAT_MANAGER, _CHAT_MANAGER_ERROR
    if PostgresChatManager is None:
        if not _CHAT_MANAGER_ERROR:
            _CHAT_MANAGER_ERROR = "multi-turn chat dependencies unavailable"
            logger.debug("chat_manager_unavailable", reason=_CHAT_MANAGER_ERROR)
        return None
    if _CHAT_MANAGER is not None:
        return _CHAT_MANAGER
    if _CHAT_MANAGER_ERROR:
        return None
    try:
        config = PostgresChatConfig.from_env()
    except Exception as exc:  # pragma: no cover - env-specific config
        _CHAT_MANAGER_ERROR = str(exc)
        logger.debug("chat_manager_config_missing", error=_CHAT_MANAGER_ERROR)
        return None
    try:
        _CHAT_MANAGER = PostgresChatManager(config=config)
    except Exception as exc:  # pragma: no cover - runtime DB connectivity
        _CHAT_MANAGER_ERROR = str(exc)
        logger.error("chat_manager_init_failed", error=_CHAT_MANAGER_ERROR)
        return None
    logger.info("chat_manager_ready")
    return _CHAT_MANAGER


class ChatHandler(BaseHTTPRequestHandler):
    server_version = "LawAPI/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - keep http.server signature
        # Reduce noise; honor LOG_REQUESTS=1 to enable
        if os.getenv("LOG_REQUESTS"):
            super().log_message(format, *args)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        parsed = urlparse(self.path)
        parts = [segment for segment in parsed.path.split("/") if segment]
        if len(parts) == 3 and parts[0] == "threads" and parts[2] == "history":
            self._handle_thread_history(parts[1])
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        if self.path.rstrip("/") == "/v1/chat/completions":
            self._handle_chat_completions()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    # ---------------- OpenAI-compatible Chat Completions -----------------

    def _handle_chat_completions(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except Exception:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            req = json.loads(raw.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
            return

        messages = req.get("messages") or []
        stream = bool(req.get("stream", False))
        model = str(req.get("model") or "gpt-5-mini-2025-08-07")
        # Optional knobs
        top_k = int(req.get("top_k") or 5)
        max_iters = int(req.get("max_iters") or 3)
        # Resolve data directory
        data_dir = Path(os.getenv("LAW_DATA_DIR") or "data")

        configure_langsmith()

        thread_id = str(req.get("thread_id") or "").strip()
        metadata = {
            "model": model,
            "stream": stream,
            "top_k": top_k,
            "max_iters": max_iters,
            "provided_thread_id": thread_id or None,
            "has_messages": bool(messages),
        }

        with trace_run("law.api.chat_completions", metadata=metadata):
            chat_result: Optional[ChatResponse] = None
            checkpoint_id: Optional[str] = None
            response_thread_id: Optional[str] = None
            manager = _get_chat_manager() if messages else None
            metadata["multi_turn_enabled"] = bool(manager)
            if manager is not None and messages:
                if not thread_id:
                    thread_id = manager.new_thread_id()
                try:
                    chat_result = manager.send_messages(
                        thread_id=thread_id, messages=messages
                    )
                    checkpoint_id = chat_result.checkpoint_id
                    response_thread_id = chat_result.thread_id
                except ValueError as exc:
                    self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                    return
                except Exception as exc:  # pragma: no cover - runtime DB/model state
                    logger.exception("chat_manager_invoke_failed", exc_info=exc)
                    chat_result = None
                    checkpoint_id = None
                    response_thread_id = None

            question = _extract_question(messages)
            created = int(time.time())
            chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

            agent_result: Optional[Dict[str, Any]] = None
            fallback_single_turn = chat_result is None or not chat_result.last_text()
            metadata["fallback_to_single_turn"] = fallback_single_turn

            if fallback_single_turn:
                if stream:
                    metadata["resolved_thread_id"] = thread_id or None
                    metadata["checkpoint_id"] = checkpoint_id
                    self._stream_single_turn_agent(
                        chat_id=chat_id,
                        model=model,
                        created=created,
                        question=question,
                        data_dir=data_dir,
                        top_k=top_k,
                        max_iters=max_iters,
                        thread_id=response_thread_id,
                        checkpoint_id=checkpoint_id,
                    )
                    return
                # Run the single-turn agent as a fallback or when multi-turn is disabled.
                agent_result = run_ask(
                    question, data_dir=data_dir, top_k=top_k, max_iters=max_iters
                )
                answer = (agent_result.get("answer") or "").strip()
            else:
                answer = chat_result.last_text()
                checkpoint_id = checkpoint_id or chat_result.checkpoint_id
                response_thread_id = response_thread_id or chat_result.thread_id

            if chat_result is not None:
                thread_id = chat_result.thread_id
                response_thread_id = response_thread_id or chat_result.thread_id

            metadata["resolved_thread_id"] = thread_id or None
            metadata["checkpoint_id"] = checkpoint_id

            tool_usage = self._collect_tool_usage(
                agent_result=agent_result, chat_result=chat_result
            )
            law_payload: Dict[str, Any] = {}
            if checkpoint_id:
                law_payload["checkpoint_id"] = checkpoint_id
            if tool_usage:
                law_payload["tool_usage"] = tool_usage

            if stream:
                self._stream_answer(
                    chat_id,
                    model,
                    created,
                    answer,
                    thread_id=response_thread_id,
                    checkpoint_id=checkpoint_id,
                    law_payload=law_payload or None,
                )
                return

            # Non-streaming response
            resp = {
                "id": chat_id,
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": answer},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": len(answer),
                    "total_tokens": len(answer),
                },
            }
            if response_thread_id:
                resp["thread_id"] = response_thread_id
            if law_payload:
                resp["law"] = law_payload
            body = _json_response(resp)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if response_thread_id:
                self.send_header("X-Thread-ID", response_thread_id)
            if checkpoint_id:
                self.send_header("X-Checkpoint-ID", checkpoint_id)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _open_stream(
        self,
        chat_id: str,
        model: str,
        created: int,
        *,
        thread_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
    ) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        if thread_id:
            self.send_header("X-Thread-ID", thread_id)
        if checkpoint_id:
            self.send_header("X-Checkpoint-ID", checkpoint_id)
        self.end_headers()

        first = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
            ],
        }
        self._sse_send(first)

    def _stream_content_chunks(
        self, chat_id: str, model: str, content: str, *, step: int = 80
    ) -> None:
        text = content or ""
        for i in range(0, len(text), step):
            piece = text[i : i + step]
            chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {"index": 0, "delta": {"content": piece}, "finish_reason": None},
                ],
            }
            self._sse_send(chunk)

    def _send_tool_usage_chunk(
        self,
        chat_id: str,
        model: str,
        usage: Dict[str, Any],
        *,
        event: str = "tool_usage.delta",
    ) -> None:
        chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": None},
            ],
            "law": {"tool_usage": usage, "event": event},
        }
        self._sse_send(chunk)

    def _close_stream(
        self,
        chat_id: str,
        model: str,
        law_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        final = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"},
            ],
        }
        if law_payload:
            payload = dict(law_payload)
            payload.setdefault("event", "tool_usage")
            final["law"] = payload
        self._sse_send(final)
        self.wfile.write(b"data: [DONE]\n\n")
        try:
            self.wfile.flush()
        except Exception:
            pass

    def _stream_single_turn_agent(
        self,
        *,
        chat_id: str,
        model: str,
        created: int,
        question: str,
        data_dir: Path,
        top_k: int,
        max_iters: int,
        thread_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
    ) -> None:
        aggregator = _ToolUsageAggregator()
        self._open_stream(
            chat_id,
            model,
            created,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
        )

        def _handle_event(event: str, payload: Dict[str, Any]) -> None:
            if aggregator.update_event(event, payload):
                snapshot = aggregator.snapshot()
                if snapshot:
                    self._send_tool_usage_chunk(
                        chat_id, model, snapshot, event="tool_usage.delta"
                    )

        agent_result = run_ask(
            question,
            data_dir=data_dir,
            top_k=top_k,
            max_iters=max_iters,
            event_callback=_handle_event,
        )
        answer = (agent_result.get("answer") or "").strip()
        tool_usage = self._collect_tool_usage(
            agent_result=agent_result, chat_result=None
        )
        aggregator.apply_final(tool_usage)
        snapshot = aggregator.snapshot()

        self._stream_content_chunks(chat_id, model, answer)

        if snapshot:
            self._send_tool_usage_chunk(
                chat_id, model, snapshot, event="tool_usage"
            )

        law_payload: Dict[str, Any] = {}
        if checkpoint_id:
            law_payload["checkpoint_id"] = checkpoint_id
        if snapshot:
            law_payload["tool_usage"] = snapshot
        self._close_stream(chat_id, model, law_payload or None)

    def _stream_answer(
        self,
        chat_id: str,
        model: str,
        created: int,
        answer: str,
        *,
        thread_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        law_payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._open_stream(
            chat_id,
            model,
            created,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
        )
        self._stream_content_chunks(chat_id, model, answer)

        if law_payload:
            tool_usage = law_payload.get("tool_usage")
            if tool_usage:
                event = str(law_payload.get("event") or "tool_usage")
                self._send_tool_usage_chunk(
                    chat_id,
                    model,
                    tool_usage,
                    event=event,
                )

        self._close_stream(chat_id, model, law_payload)

    def _handle_thread_history(self, thread_id: str) -> None:
        manager = _get_chat_manager()
        if manager is None:
            self.send_error(
                HTTPStatus.SERVICE_UNAVAILABLE, "Multi-turn chat is not configured"
            )
            return
        try:
            history = manager.get_history(thread_id)
        except ValueError as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        payload = {"thread_id": thread_id, "history": history}
        body = _json_response(payload)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _collect_tool_usage(
        self,
        *,
        agent_result: Optional[Dict[str, Any]],
        chat_result: Optional[ChatResponse],
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {}

        if agent_result:
            actions = agent_result.get("actions") or []
            if actions:
                payload["actions"] = actions
            queries = agent_result.get("queries") or agent_result.get("used_queries")
            if queries:
                payload["queries"] = queries
            iters = agent_result.get("iters")
            if isinstance(iters, int):
                payload["iterations"] = iters
            error = agent_result.get("error")
            if error:
                payload["error"] = str(error)

        if chat_result and chat_result.response:
            tool_calls = chat_result.response.get("tool_calls")
            if tool_calls:
                payload["tool_calls"] = tool_calls

        return payload or None

    def _sse_send(self, obj: Dict[str, Any]) -> None:
        data = json.dumps(obj, ensure_ascii=False)
        try:
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
        except Exception:
            # Client disconnected
            pass


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    configure_langsmith()
    server = ThreadingHTTPServer((host, port), ChatHandler)
    print(f"[law] OpenAI-compatible server listening on http://{host}:{port}")
    print("  POST /v1/chat/completions  {model, messages, stream}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

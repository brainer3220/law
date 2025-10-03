from __future__ import annotations

import json
import logging
import os
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple
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


def _normalize_tool_calls(
    tool_calls: Optional[Any],
) -> List[Dict[str, Any]]:
    """Coerce LangChain tool call payloads into OpenAI-compatible dictionaries."""

    if not tool_calls:
        return []

    if isinstance(tool_calls, Iterable) and not isinstance(tool_calls, (str, bytes)):
        candidates = list(tool_calls)
    else:
        logger.warning(
            "tool_call_payload_not_iterable", payload_type=type(tool_calls).__name__
        )
        return []

    normalized: List[Dict[str, Any]] = []
    for index, raw_call in enumerate(candidates):
        call: Optional[Dict[str, Any]]
        if isinstance(raw_call, dict):
            call = dict(raw_call)
        else:
            call = _serialize_tool_call_object(raw_call)
        if not call:
            logger.warning(
                "Malformed tool call at index %d: expected dict, got %s (%r)",
                index,
                type(raw_call).__name__,
                raw_call,
            )
            continue
        fn: Dict[str, Any] = {}
        raw_fn = call.get("function")
        if isinstance(raw_fn, dict):
            fn = dict(raw_fn)
        elif raw_fn is not None:
            fn = _serialize_tool_function(raw_fn)
        name = str(fn.get("name") or call.get("name") or "")
        raw_args: Any = fn.get("arguments")
        if raw_args is None and "args" in call:
            raw_args = call["args"]
        if isinstance(raw_args, (dict, list)):
            arguments = json.dumps(raw_args, ensure_ascii=False)
        elif raw_args is None:
            arguments = ""
        else:
            arguments = str(raw_args)
        call_id = (
            call.get("id")
            or call.get("tool_call_id")
            or f"call_{index:04d}_{uuid.uuid4().hex[:8]}"
        )

        normalized.append(
            {
                "id": str(call_id),
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
        )
    return normalized


def _normalize_tool_call_chunk(chunk: Any) -> List[Dict[str, Any]]:
    """Normalize a raw tool call chunk payload into OpenAI delta format."""

    def _coerce(entry: Any) -> Optional[Dict[str, Any]]:
        if entry is None:
            return None
        if isinstance(entry, dict):
            data = dict(entry)
        else:
            data = _serialize_tool_call_object(entry) or {}
        if not data:
            return None
        fn = data.get("function")
        if isinstance(fn, dict):
            fn_data = dict(fn)
            args = fn_data.get("arguments")
            if isinstance(args, (dict, list)):
                fn_data["arguments"] = json.dumps(args, ensure_ascii=False)
            elif args is None:
                fn_data["arguments"] = ""
            fn_name = fn_data.get("name")
            if fn_name is not None:
                fn_data["name"] = str(fn_name)
            data["function"] = fn_data
        return data

    def _collect(value: Any) -> List[Dict[str, Any]]:
        if value is None:
            return []
        if isinstance(value, dict):
            if "tool_calls" in value:
                tool_calls = value.get("tool_calls")
                if isinstance(tool_calls, Iterable) and not isinstance(
                    tool_calls, (str, bytes)
                ):
                    items = [_coerce(item) for item in tool_calls]
                    return [item for item in items if item]
            if "delta" in value:
                return _collect(value.get("delta"))
            if "choices" in value:
                choices = value.get("choices")
                collected: List[Dict[str, Any]] = []
                if isinstance(choices, Iterable) and not isinstance(
                    choices, (str, bytes)
                ):
                    for choice in choices:
                        collected.extend(_collect(choice))
                return collected
            call = _coerce(value)
            return [call] if call else []
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            aggregated: List[Dict[str, Any]] = []
            for item in value:
                aggregated.extend(_collect(item))
            return aggregated
        call = _coerce(value)
        return [call] if call else []

    normalized = _collect(chunk)
    indexed: List[Dict[str, Any]] = []
    for fallback_index, call in enumerate(normalized):
        data = dict(call)
        index_value = data.get("index")
        if isinstance(index_value, int):
            index = index_value
        else:
            try:
                index = int(index_value)
            except (TypeError, ValueError):
                index = fallback_index
        data["index"] = index
        if data.get("type") is None:
            data["type"] = "function"
        indexed.append(data)

    return indexed


def _serialize_tool_function(raw_fn: Any) -> Dict[str, Any]:
    if isinstance(raw_fn, dict):
        return dict(raw_fn)
    fn: Dict[str, Any] = {}
    for key in ("name", "arguments", "args"):
        if hasattr(raw_fn, key):
            value = getattr(raw_fn, key)
            if key == "args" and "arguments" not in fn:
                fn["arguments"] = value
            else:
                fn[key] = value
    if "arguments" not in fn and hasattr(raw_fn, "kwargs"):
        fn["arguments"] = getattr(raw_fn, "kwargs")
    return fn


def _serialize_tool_call_object(call: Any) -> Optional[Dict[str, Any]]:
    if call is None:
        return None
    data: Dict[str, Any] = {}
    for key in ("id", "tool_call_id", "name", "args", "function"):
        if hasattr(call, key):
            value = getattr(call, key)
            if key == "function" and value is not None:
                data[key] = _serialize_tool_function(value)
            else:
                data[key] = value
    if hasattr(call, "arguments") and "args" not in data:
        data["args"] = getattr(call, "arguments")
    if not data:
        return None
    return data


def _extract_tool_payloads(
    payload: Optional[Any],
) -> Tuple[List[Any], List[Any]]:
    tool_calls: List[Any] = []
    tool_call_chunks: List[Any] = []
    if not payload:
        return tool_calls, tool_call_chunks

    if isinstance(payload, dict):
        candidate_calls = payload.get("tool_calls")
        candidate_chunks = payload.get("tool_call_chunks")
    else:
        candidate_calls = getattr(payload, "tool_calls", None)
        candidate_chunks = getattr(payload, "tool_call_chunks", None)

    if isinstance(candidate_calls, Iterable) and not isinstance(
        candidate_calls, (str, bytes)
    ):
        tool_calls = list(candidate_calls)
    elif candidate_calls:
        logger.warning(
            "unexpected_tool_calls_payload", payload_type=type(candidate_calls).__name__
        )

    if isinstance(candidate_chunks, Iterable) and not isinstance(
        candidate_chunks, (str, bytes)
    ):
        tool_call_chunks = list(candidate_chunks)
    elif candidate_chunks:
        logger.warning(
            "unexpected_tool_call_chunks_payload",
            payload_type=type(candidate_chunks).__name__,
        )

    return tool_calls, tool_call_chunks


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
            stream_iterator: Optional[Iterator[Dict[str, Any]]] = None
            manager = _get_chat_manager() if messages else None
            metadata["multi_turn_enabled"] = bool(manager)
            if manager is not None and messages:
                if not thread_id:
                    thread_id = manager.new_thread_id()
                if stream:
                    stream_method = getattr(manager, "stream_messages", None)
                    if callable(stream_method):
                        try:
                            stream_iterator = stream_method(
                                thread_id=thread_id, messages=messages
                            )
                        except ValueError as exc:
                            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
                            return
                        except Exception as exc:  # pragma: no cover - runtime DB/model state
                            logger.exception("chat_manager_stream_failed", exc_info=exc)
                            metadata["stream_generator_error"] = str(exc)
                            stream_iterator = None
                    else:
                        metadata["stream_generator_error"] = "unavailable"
                if stream_iterator is None:
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
                else:
                    response_thread_id = thread_id

            question = _extract_question(messages)
            created = int(time.time())
            chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

            agent_result: Optional[Dict[str, Any]] = None
            using_stream_iterator = bool(stream and stream_iterator is not None)
            answer: str = ""
            if using_stream_iterator:
                metadata["fallback_to_single_turn"] = False
            elif chat_result is None or not chat_result.last_text():
                # Run the single-turn agent as a fallback or when multi-turn is disabled.
                agent_result = run_ask(
                    question, data_dir=data_dir, top_k=top_k, max_iters=max_iters
                )
                answer = (agent_result.get("answer") or "").strip()
                metadata["fallback_to_single_turn"] = True
            else:
                answer = chat_result.last_text()
                checkpoint_id = checkpoint_id or chat_result.checkpoint_id
                response_thread_id = response_thread_id or chat_result.thread_id
                metadata["fallback_to_single_turn"] = False

            if chat_result is not None:
                thread_id = chat_result.thread_id
                response_thread_id = response_thread_id or chat_result.thread_id

            metadata["resolved_thread_id"] = thread_id or None
            metadata["checkpoint_id"] = checkpoint_id

            if stream and stream_iterator is not None:
                final_chat = self._stream_answer(
                    chat_id,
                    model,
                    created,
                    thread_id=response_thread_id,
                    checkpoint_id=checkpoint_id,
                    law_payload=None,
                    tool_calls=None,
                    tool_call_chunks=None,
                    fallback_answer="",
                    event_iterator=stream_iterator,
                    agent_result=None,
                    chat_result=None,
                )
                if final_chat is not None:
                    checkpoint_id = checkpoint_id or final_chat.checkpoint_id
                    metadata["checkpoint_id"] = checkpoint_id
                    metadata["resolved_thread_id"] = (
                        final_chat.thread_id or thread_id or response_thread_id or None
                    )
                else:
                    metadata["resolved_thread_id"] = response_thread_id or thread_id or None
                return

            tool_usage = self._collect_tool_usage(
                agent_result=agent_result, chat_result=chat_result
            )
            response_payload: Optional[Any] = (
                chat_result.response if chat_result else None
            )
            raw_tool_calls, raw_tool_call_chunks = _extract_tool_payloads(
                response_payload
            )
            formatted_tool_calls = _normalize_tool_calls(raw_tool_calls)
            law_payload: Dict[str, Any] = {}
            if checkpoint_id:
                law_payload["checkpoint_id"] = checkpoint_id
            if tool_usage:
                law_payload["tool_usage"] = tool_usage
            if raw_tool_calls:
                law_payload["tool_calls"] = raw_tool_calls
            if raw_tool_call_chunks:
                law_payload["tool_call_chunks"] = raw_tool_call_chunks

            if stream:
                final_chat = self._stream_answer(
                    chat_id,
                    model,
                    created,
                    thread_id=response_thread_id,
                    checkpoint_id=checkpoint_id,
                    law_payload=law_payload or None,
                    tool_calls=formatted_tool_calls,
                    tool_call_chunks=raw_tool_call_chunks,
                    fallback_answer=answer,
                    event_iterator=None,
                    agent_result=agent_result,
                    chat_result=chat_result,
                )
                if final_chat is not None:
                    checkpoint_id = checkpoint_id or final_chat.checkpoint_id
                    metadata["checkpoint_id"] = checkpoint_id
                    metadata["resolved_thread_id"] = (
                        final_chat.thread_id or response_thread_id or thread_id or None
                    )
                else:
                    metadata["resolved_thread_id"] = response_thread_id or thread_id or None
                return

            # Non-streaming response
            message: Dict[str, Any] = {
                "role": "assistant",
                "content": answer or None,
            }
            if formatted_tool_calls:
                message["tool_calls"] = formatted_tool_calls
            resp = {
                "id": chat_id,
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": message,
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

    def _stream_answer(
        self,
        chat_id: str,
        model: str,
        created: int,
        *,
        thread_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        law_payload: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_chunks: Optional[List[Any]] = None,
        fallback_answer: str = "",
        event_iterator: Optional[Iterator[Dict[str, Any]]] = None,
        agent_result: Optional[Dict[str, Any]] = None,
        chat_result: Optional[ChatResponse] = None,
    ) -> Optional[ChatResponse]:
        # Prepare headers for SSE-compatible streaming
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        if thread_id:
            self.send_header("X-Thread-ID", thread_id)
        if checkpoint_id:
            self.send_header("X-Checkpoint-ID", checkpoint_id)
        self.end_headers()

        # First chunk with role and optional tool call metadata
        delta: Dict[str, Any] = {"role": "assistant"}
        if tool_calls:
            delta["tool_calls"] = [
                {
                    "index": idx,
                    "id": call["id"],
                    "type": call["type"],
                    "function": call["function"],
                }
                for idx, call in enumerate(tool_calls)
            ]
        first = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
        }
        self._sse_send(first)

        final_response: Optional[ChatResponse] = chat_result
        collected_tool_call_chunks: List[Any] = []
        if tool_call_chunks:
            collected_tool_call_chunks.extend(tool_call_chunks)

        if event_iterator is not None:
            iterator = iter(event_iterator)
            while True:
                try:
                    event = next(iterator)
                except StopIteration as stop:
                    value = getattr(stop, "value", None)
                    if isinstance(value, ChatResponse):
                        final_response = value
                    break
                except Exception as exc:  # pragma: no cover - streaming failure
                    logger.exception("stream_iterator_failed", exc_info=exc)
                    break

                if isinstance(event, dict):
                    event_type = event.get("type")
                    payload = event.get("payload")
                else:
                    event_type = None
                    payload = event

                if event_type == "content_delta":
                    text_delta = "" if payload is None else str(payload)
                    if not text_delta:
                        continue
                    chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": text_delta},
                                "finish_reason": None,
                            }
                        ],
                    }
                    self._sse_send(chunk)
                elif event_type == "tool_call_chunk":
                    if payload is None:
                        continue
                    collected_tool_call_chunks.append(payload)
                    normalized_chunks = _normalize_tool_call_chunk(payload)
                    if not normalized_chunks:
                        continue
                    chunk_payload = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"tool_calls": normalized_chunks},
                                "finish_reason": None,
                            }
                        ],
                    }
                    self._sse_send(chunk_payload)
                else:
                    # Ignore unrecognized events
                    continue
        else:
            # Emit intermediate tool call chunks prior to the textual content
            if tool_call_chunks:
                for raw_chunk in tool_call_chunks:
                    normalized_chunks = _normalize_tool_call_chunk(raw_chunk)
                    if not normalized_chunks:
                        continue
                    chunk_payload = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"tool_calls": normalized_chunks},
                                "finish_reason": None,
                            }
                        ],
                    }
                    self._sse_send(chunk_payload)

            # Stream the content in pieces
            content = fallback_answer or ""
            # Chunk by ~80 characters to simulate token stream
            step = 80
            for i in range(0, len(content), step):
                piece = content[i : i + step]
                if not piece:
                    continue
                chunk = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": piece},
                            "finish_reason": None,
                        }
                    ],
                }
                self._sse_send(chunk)

        combined_law_payload: Dict[str, Any] = dict(law_payload or {})
        final_tool_usage = self._collect_tool_usage(
            agent_result=agent_result, chat_result=final_response
        )
        if final_tool_usage:
            combined_law_payload["tool_usage"] = final_tool_usage

        if final_response is not None:
            checkpoint_id = checkpoint_id or final_response.checkpoint_id
            raw_tool_calls, response_tool_chunks = _extract_tool_payloads(
                final_response.response
            )
            if raw_tool_calls:
                combined_law_payload["tool_calls"] = raw_tool_calls
            if response_tool_chunks:
                combined_law_payload["tool_call_chunks"] = response_tool_chunks
        if collected_tool_call_chunks and "tool_call_chunks" not in combined_law_payload:
            combined_law_payload["tool_call_chunks"] = collected_tool_call_chunks
        if checkpoint_id and "checkpoint_id" not in combined_law_payload:
            combined_law_payload["checkpoint_id"] = checkpoint_id

        final_payload = combined_law_payload or None

        # Final empty delta with finish_reason=stop
        final_chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"},
            ],
        }
        if final_payload:
            final_chunk["law"] = final_payload
        self._sse_send(final_chunk)
        # End of stream marker
        self.wfile.write(b"data: [DONE]\n\n")
        try:
            self.wfile.flush()
        except Exception:
            pass

        return final_response

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

        if chat_result:
            tool_calls, tool_call_chunks = _extract_tool_payloads(chat_result.response)
            if tool_calls:
                payload["tool_calls"] = tool_calls
            if tool_call_chunks:
                payload["tool_call_chunks"] = tool_call_chunks

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

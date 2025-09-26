from __future__ import annotations

import json
import os
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from packages.legal_tools.agent_graph import run_ask


def _partition_history_and_question(
    messages: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, str]], str]:
    """Split OpenAI-style chat messages into history and the latest question."""

    normalized: List[Dict[str, str]] = []
    last_user_index: Optional[int] = None

    for raw in messages:
        role = str(raw.get("role", "")).strip().lower()
        content = str(raw.get("content", ""))
        if not content:
            continue
        if role not in {"system", "user", "assistant"}:
            continue
        normalized.append({"role": role, "content": content})
        if role == "user":
            last_user_index = len(normalized) - 1

    if last_user_index is None:
        return normalized, ""

    question = normalized[last_user_index]["content"]
    history = normalized[:last_user_index]
    return history, question


def _json_response(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


class ChatHandler(BaseHTTPRequestHandler):
    server_version = "LawAPI/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - keep http.server signature
        # Reduce noise; honor LOG_REQUESTS=1 to enable
        if os.getenv("LOG_REQUESTS"):
            super().log_message(format, *args)

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

        history, question = _partition_history_and_question(messages)
        created = int(time.time())
        chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

        # Run the agent (blocking). We stream the resulting answer in chunks if requested.
        result = run_ask(
            question,
            data_dir=data_dir,
            top_k=top_k,
            max_iters=max_iters,
            history=history,
        )
        answer: str = (result.get("answer") or "").strip()

        if stream:
            self._stream_answer(chat_id, model, created, answer)
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
        body = _json_response(resp)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _stream_answer(
        self, chat_id: str, model: str, created: int, answer: str
    ) -> None:
        # Prepare headers for SSE-compatible streaming
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        # First chunk with role
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

        # Stream the content in pieces
        content = answer or ""
        # Chunk by ~80 characters to simulate token stream
        step = 80
        for i in range(0, len(content), step):
            piece = content[i : i + step]
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

        # Final empty delta with finish_reason=stop
        final = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"},
            ],
        }
        self._sse_send(final)
        # End of stream marker
        self.wfile.write(b"data: [DONE]\n\n")
        try:
            self.wfile.flush()
        except Exception:
            pass

    def _sse_send(self, obj: Dict[str, Any]) -> None:
        data = json.dumps(obj, ensure_ascii=False)
        try:
            self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
            self.wfile.flush()
        except Exception:
            # Client disconnected
            pass


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), ChatHandler)
    print(f"[law] OpenAI-compatible server listening on http://{host}:{port}")
    print("  POST /v1/chat/completions  {model, messages, stream}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

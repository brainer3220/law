"""FastAPI application exposing the OpenAI-compatible endpoints for Vercel."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterable, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from packages.legal_tools.agent_graph import run_ask
from packages.legal_tools.api_server import _extract_question
from packages.legal_tools.tracing import configure_langsmith, trace_run

__all__ = ["app"]

app = FastAPI(title="Law API", version="1.0.0")


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _chunk_text(content: str, step: int = 80) -> Iterable[str]:
    content = content or ""
    for index in range(0, len(content), step):
        piece = content[index : index + step]
        if piece:
            yield piece


def _collect_tool_usage(agent_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not agent_result:
        return None
    payload: Dict[str, Any] = {}
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
    return payload or None


def _streaming_response(
    *,
    answer: str,
    chat_id: str,
    model: str,
    law_payload: Optional[Dict[str, Any]],
) -> StreamingResponse:
    async def event_iterator() -> AsyncIterator[str]:
        for piece in _chunk_text(answer):
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
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        final_chunk: Dict[str, Any] = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }
        if law_payload:
            final_chunk["law"] = law_payload
        yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_iterator(), media_type="text/event-stream")


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> JSONResponse | StreamingResponse:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    messages = payload.get("messages") or []
    stream = bool(payload.get("stream", False))
    model = str(payload.get("model") or "gpt-5-mini-2025-08-07")
    top_k = _coerce_int(payload.get("top_k"), 5)
    max_iters = _coerce_int(payload.get("max_iters"), 3)

    question = _extract_question(messages)
    if not question:
        raise HTTPException(status_code=400, detail="No user question provided")

    data_dir = Path(os.getenv("LAW_DATA_DIR") or "data")
    created = int(time.time())
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

    configure_langsmith()
    metadata = {
        "model": model,
        "stream": stream,
        "top_k": top_k,
        "max_iters": max_iters,
        "has_messages": bool(messages),
    }

    with trace_run("law.vercel.chat_completions", metadata=metadata):
        try:
            agent_result = run_ask(
                question,
                data_dir=data_dir,
                top_k=top_k,
                max_iters=max_iters,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    answer = (agent_result.get("answer") or "").strip()
    usage = {
        "prompt_tokens": 0,
        "completion_tokens": len(answer),
        "total_tokens": len(answer),
    }
    law_payload = _collect_tool_usage(agent_result)

    if stream:
        return _streaming_response(
            answer=answer,
            chat_id=chat_id,
            model=model,
            law_payload=law_payload,
        )

    message: Dict[str, Any] = {
        "role": "assistant",
        "content": answer or None,
    }

    response = {
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
        "usage": usage,
    }
    if law_payload:
        response["law"] = {"tool_usage": law_payload}

    return JSONResponse(response)

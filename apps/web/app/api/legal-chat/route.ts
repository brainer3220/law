import { requireAuthenticatedUserId } from "../auth/require-user";
import { callLawApi, forwardLawApiResponse } from "./service";

export async function POST(request: Request): Promise<Response> {
  try {
    const userId = await requireAuthenticatedUserId();
    if (userId instanceof Response) {
      return userId;
    }
    const payload = await request.json();
    const stream = payload.stream ?? true;
    const upstream = await callLawApi("/v1/chat/completions", {
      method: "POST",
      actorId: userId,
      body: JSON.stringify({
        model: payload.model ?? "gpt-5-mini-2025-08-07",
        messages: payload.messages ?? [],
        stream,
        top_k: payload.top_k ?? 5,
        max_iters: payload.max_iters ?? 3,
      }),
    });
    if (stream) {
      return forwardStreamingLawApiResponse(upstream);
    }
    return forwardLawApiResponse(upstream);
  } catch (error) {
    console.error("[legal-chat] Failed to reach law API", error);
    return new Response(
      JSON.stringify({ error: "Unable to reach legal QA service" }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

function forwardStreamingLawApiResponse(upstream: Response): Response {
  const headers = new Headers();
  headers.set(
    "Content-Type",
    upstream.headers.get("content-type") ?? "text/event-stream; charset=utf-8"
  );
  headers.set("Cache-Control", "no-cache, no-transform");
  const threadId = upstream.headers.get("x-thread-id");
  const checkpointId = upstream.headers.get("x-checkpoint-id");
  if (threadId) {
    headers.set("X-Thread-ID", threadId);
  }
  if (checkpointId) {
    headers.set("X-Checkpoint-ID", checkpointId);
  }
  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers,
  });
}

import { callLawApi, forwardLawApiResponse } from "./service";

export async function POST(request: Request): Promise<Response> {
  try {
    const payload = await request.json();
    const upstream = await callLawApi("/v1/chat/completions", {
      method: "POST",
      body: JSON.stringify({
        model: payload.model ?? "gpt-5-mini-2025-08-07",
        messages: payload.messages ?? [],
        stream: false,
        top_k: payload.top_k ?? 5,
        max_iters: payload.max_iters ?? 3,
      }),
    });
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

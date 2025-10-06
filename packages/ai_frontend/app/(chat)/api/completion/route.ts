import { streamText } from "ai";
import { openai } from "@ai-sdk/openai";

export const runtime = "edge";

type CompletionRequestBody = {
  prompt: string;
};

export async function POST(request: Request) {
  let prompt: string;

  try {
    const body = (await request.json()) as CompletionRequestBody;
    if (typeof body.prompt !== "string") {
      return new Response("Missing prompt", { status: 400 });
    }
    prompt = body.prompt.trim();
  } catch {
    return new Response("Invalid request body", { status: 400 });
  }

  if (!prompt) {
    return new Response("Missing prompt", { status: 400 });
  }

  try {
    const response = await streamText({
      model: openai("gpt-4o"),
      prompt,
    });

    return response.toTextStreamResponse();
  } catch (error) {
    console.error("/api/completion failed", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}
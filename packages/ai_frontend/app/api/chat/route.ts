import { z } from "zod";
import { streamText, tool, stepCountIs } from "ai";
import { createOpenAI } from "@ai-sdk/openai";

const llm = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY ?? "",
  baseURL: process.env.OPENAI_BASE_URL,
});

export const runtime = "edge";

const webSearchResultSchema = z.object({
  query: z.string(),
  hits: z.array(z.object({ title: z.string(), url: z.string().url() })),
});

type ToolEvent =
  | {
      type: "tool-status";
      callId: string;
      toolName: string;
      status: "started" | "running" | "success" | "error";
      message?: string;
      elapsedMs?: number;
    }
  | {
      type: "tool-result";
      callId: string;
      toolName: string;
      status?: "success" | "error";
      result: unknown;
      elapsedMs?: number;
    };

export async function POST(req: Request) {
  const { messages } = await req.json();

  const toolEvents: ToolEvent[] = [];
  const pushEvent = (event: ToolEvent) => {
    toolEvents.push(event);
  };

  const result = await streamText({
    model: llm(process.env.OPENAI_MODEL ?? "gpt-4o-mini"),
    messages,
    tools: {
      webSearch: tool({
        description: "간단한 웹 검색 후 상위 문서 요약",
        inputSchema: z.object({ q: z.string().min(1) }),
        async execute({ q }) {
          const start = Date.now();
          const callId = crypto.randomUUID();
          pushEvent({
            type: "tool-status",
            callId,
            toolName: "webSearch",
            status: "started",
            message: `검색 질의 전송: ${q}`,
          });

          const payload = {
            query: q,
            hits: [
              { title: "Example", url: "https://example.com" },
              { title: "법령정보", url: "https://law.go.kr" },
            ],
          } satisfies z.infer<typeof webSearchResultSchema>;

          const elapsedMs = Date.now() - start;
          pushEvent({
            type: "tool-result",
            callId,
            toolName: "webSearch",
            status: "success",
            result: payload,
            elapsedMs,
          });

          return payload;
        },
      }),
      getWeather: tool({
        description: "도시 현재 기온 조회",
        inputSchema: z.object({ city: z.string() }),
        async execute({ city }) {
          const callId = crypto.randomUUID();
          const start = Date.now();
          pushEvent({
            type: "tool-status",
            callId,
            toolName: "getWeather",
            status: "running",
            message: `${city} 날씨를 조회 중입니다`,
          });

          const result = { city, tempC: 24.3 };
          const elapsedMs = Date.now() - start;
          pushEvent({
            type: "tool-result",
            callId,
            toolName: "getWeather",
            status: "success",
            result,
            elapsedMs,
          });
          return result;
        },
      }),
    },
    stopWhen: stepCountIs(5),
    onStepFinish({ toolCalls, toolResults }) {
      for (const call of toolCalls ?? []) {
        pushEvent({
          type: "tool-status",
          callId: call.callId,
          toolName: call.toolName,
          status: "success",
          message: "도구 호출 완료",
        });
      }

      for (const result of toolResults ?? []) {
        pushEvent({
          type: "tool-result",
          callId: result.callId,
          toolName: result.toolName,
          status: "success",
          result: result.result,
        });
      }
    },
  });

  const response = result.toAIStreamResponse();
  response.headers.set("X-Tool-Events", encodeURIComponent(JSON.stringify(toolEvents)));
  return response;
}

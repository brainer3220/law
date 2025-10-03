import { simulateReadableStream, tool } from "ai";
import type { LanguageModelUsage, UIMessageStreamWriter } from "ai";
import { MockLanguageModelV2 } from "ai/test";
import { expect, test } from "@playwright/test";
import { z } from "zod";
import {
  runAgent,
  getAgentActiveTools,
  DEFAULT_CHAT_TOOL_NAMES,
} from "@/lib/ai/agent";
import type { ChatMessage, ChatTools } from "@/lib/types";

const mockModel = new MockLanguageModelV2({
  doGenerate: async () => ({
    rawCall: { rawPrompt: null, rawSettings: {} },
    finishReason: "stop",
    usage: { inputTokens: 1, outputTokens: 2, totalTokens: 3 },
    content: [{ type: "text", text: "Mock response" }],
    warnings: [],
  }),
  doStream: async () => ({
    rawCall: { rawPrompt: null, rawSettings: {} },
    stream: simulateReadableStream({
      chunkDelayInMs: 0,
      initialDelayInMs: 0,
      chunks: [
        { id: "1", type: "text-start" },
        { id: "1", type: "text-delta", delta: "Mock response" },
        { id: "1", type: "text-end" },
        {
          type: "finish",
          finishReason: "stop",
          usage: { inputTokens: 1, outputTokens: 2, totalTokens: 3 },
        },
      ],
    }),
  }),
});

test("getAgentActiveTools disables tool access for reasoning model", () => {
  expect(getAgentActiveTools("chat-model-reasoning")).toEqual([]);
  expect(getAgentActiveTools("chat-model")).toEqual([
    ...DEFAULT_CHAT_TOOL_NAMES,
  ]);
});

test("runAgent streams a response with the provided model", async () => {
  const writes: unknown[] = [];
  const dataStream: UIMessageStreamWriter<ChatMessage> = {
    write: (part) => {
      writes.push(part);
    },
    merge: () => {
      // no-op for unit tests
    },
    onError: undefined,
  };

  const requestHints = {
    latitude: 0,
    longitude: 0,
    city: "Seoul",
    country: "KR",
  };

  const uiMessages: ChatMessage[] = [
    {
      id: "msg-1",
      role: "user",
      content: "Hello there",
      parts: [{ type: "text", text: "Hello there" }],
      createdAt: new Date().toISOString(),
    },
  ];

  const stubTools = {
    getWeather: tool({
      description: "stub weather",
      inputSchema: z.object({}),
      execute: async () => ({ ok: true }),
    }),
    createDocument: tool({
      description: "stub create document",
      inputSchema: z.object({}),
      execute: async () => ({ id: "doc" }),
    }),
    updateDocument: tool({
      description: "stub update document",
      inputSchema: z.object({}),
      execute: async () => ({ id: "doc" }),
    }),
    requestSuggestions: tool({
      description: "stub suggestions",
      inputSchema: z.object({}),
      execute: async () => ({ suggestions: [] }),
    }),
    lawKeywordSearch: tool({
      description: "stub law keyword",
      inputSchema: z.object({}),
      execute: async () => ({ results: [] }),
    }),
    lawStatuteSearch: tool({
      description: "stub law statute search",
      inputSchema: z.object({}),
      execute: async () => ({ results: [] }),
    }),
    lawStatuteDetail: tool({
      description: "stub law statute detail",
      inputSchema: z.object({}),
      execute: async () => ({ detail: null }),
    }),
    lawInterpretationSearch: tool({
      description: "stub law interpretation search",
      inputSchema: z.object({}),
      execute: async () => ({ results: [] }),
    }),
    lawInterpretationDetail: tool({
      description: "stub law interpretation detail",
      inputSchema: z.object({}),
      execute: async () => ({ detail: null }),
    }),
  } as unknown as ChatTools;

  let capturedUsage: LanguageModelUsage | undefined;

  const result = runAgent({
    dataStream,
    tools: stubTools,
    model: mockModel,
    onFinish: async ({ usage }) => {
      capturedUsage = usage;
    },
    requestHints,
    selectedChatModel: "chat-model",
    uiMessages,
  });

  await expect(result.text).resolves.toBe("Mock response");

  const usage = await result.totalUsage;
  expect(usage).toEqual({ inputTokens: 1, outputTokens: 2, totalTokens: 3 });
  expect(capturedUsage).toEqual(usage);
  expect(writes).toEqual([]);
});

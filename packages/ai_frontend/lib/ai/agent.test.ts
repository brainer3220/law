import type { UIMessageStreamWriter } from "ai";
import type { Session } from "next-auth";
import { z } from "zod";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatMessage } from "../types";
import type { RequestHints } from "./prompts";

const streamTextMock = vi.fn();

vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return {
    ...actual,
    streamText: streamTextMock,
  };
});

const { tool } = await vi.importActual<typeof import("ai")>("ai");

describe("runAgent", () => {
  const session = {
    user: {
      id: "user-1",
      name: "Test User",
      email: "test@example.com",
      type: "standard",
    },
    expires: new Date().toISOString(),
  } as unknown as Session;

  const requestHints: RequestHints = {
    latitude: 37.5665,
    longitude: 126.978,
    city: "Seoul",
    country: "KR",
  };

  const userMessage: ChatMessage = {
    id: "message-1",
    role: "user",
    content: "What's the weather like in Seoul?",
    createdAt: new Date().toISOString(),
    parts: [
      { type: "text", text: "What's the weather like in Seoul?" },
    ],
  };

  beforeEach(() => {
    streamTextMock.mockReset();
  });

  it("configures streamText with tool support and propagates finish events", async () => {
    const { runAgent } = await import("./agent");

    const toolInvocations: Array<unknown> = [];
    const writes: Array<unknown> = [];
    const usageHandler = vi.fn();

    const dataStream: UIMessageStreamWriter<ChatMessage> = {
      write: (part) => {
        writes.push(part);
      },
      merge: vi.fn(),
      onError: undefined,
    };

    const testTool = tool({
      description: "Returns a canned forecast",
      inputSchema: z.object({ city: z.string() }),
      execute: async ({ city }) => {
        toolInvocations.push(city);
        return { forecast: "Sunny" };
      },
    });

    const mockSteps = [
      { finishReason: "tool-calls", toolCalls: [{ toolName: "testTool" }] },
      { finishReason: "stop", toolCalls: [] },
    ];

    const mockStreamResult = {
      consumeStream: vi.fn().mockResolvedValue(undefined),
      steps: Promise.resolve(mockSteps as any),
      text: Promise.resolve("It is sunny in Seoul today."),
      toUIMessageStream: vi.fn(),
      toolCalls: Promise.resolve([{ toolName: "testTool" }] as any),
    };

    let capturedOptions: any;
    const mockUsage = { inputTokens: 5, outputTokens: 10, totalTokens: 15 };

    streamTextMock.mockImplementationOnce((options: any) => {
      capturedOptions = options;
      options.onFinish?.({ usage: mockUsage });
      return mockStreamResult;
    });

    const result = await runAgent({
      selectedChatModel: "chat-model",
      requestHints,
      uiMessages: [userMessage],
      session,
      dataStream,
      model: "mock-model",
      tools: { testTool },
      activeTools: ["testTool"],
      includeDefaultTools: false,
      onFinish: usageHandler,
    });

    expect(streamTextMock).toHaveBeenCalledTimes(1);
    expect(capturedOptions).toBeDefined();
    expect(Array.isArray(capturedOptions.messages)).toBe(true);
    expect(capturedOptions.activeTools).toEqual(["testTool"]);
    expect(typeof capturedOptions.stopWhen).toBe("function");

    await capturedOptions.tools.testTool.execute({ city: "Seoul" });
    expect(toolInvocations).toEqual(["Seoul"]);

    await result.consumeStream();
    expect(await result.steps).toEqual(mockSteps);
    expect(await result.text).toBe("It is sunny in Seoul today.");

    expect(usageHandler).toHaveBeenCalledWith({ usage: mockUsage });
    expect(writes).toEqual([]);
  });
});

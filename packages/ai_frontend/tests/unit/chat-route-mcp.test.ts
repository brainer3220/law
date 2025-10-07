import { beforeEach, describe, expect, test, vi } from "vitest";

const mockStreamText = vi.fn();
const mockCreateUIMessageStream = vi.fn();
const mockLoadMcpTools = vi.fn();

vi.mock("@vercel/functions", () => ({
  geolocation: vi.fn(() => ({
    longitude: 10,
    latitude: 20,
    city: "Test City",
    country: "Test Country",
  })),
}));

vi.mock("ai", () => ({
  convertToModelMessages: vi.fn((messages) => messages),
  createUIMessageStream: mockCreateUIMessageStream,
  JsonToSseTransformStream: class {},
  smoothStream: vi.fn(() => (value: unknown) => value),
  stepCountIs: vi.fn(() => false),
  streamText: mockStreamText,
}));

vi.mock("@/lib/ai/mcp", () => ({
  loadMcpTools: mockLoadMcpTools,
}));

vi.mock("@/app/(auth)/auth", () => ({
  auth: vi.fn(async () => ({
    user: { id: "user-1", type: "regular" },
  })),
}));

vi.mock("@/lib/ai/entitlements", () => ({
  entitlementsByUserType: {
    regular: { maxMessagesPerDay: 100, availableChatModelIds: ["chat-model"] },
  },
}));

vi.mock("@/lib/ai/providers", () => ({
  myProvider: {
    languageModel: vi.fn(() => ({ modelId: "mock-model" })),
  },
}));

vi.mock("@/lib/ai/prompts", () => ({
  systemPrompt: vi.fn(() => "system"),
}));

vi.mock("@/lib/ai/tools/create-document", () => ({
  createDocument: vi.fn(() => "createDocumentTool"),
}));

vi.mock("@/lib/ai/tools/update-document", () => ({
  updateDocument: vi.fn(() => "updateDocumentTool"),
}));

vi.mock("@/lib/ai/tools/request-suggestions", () => ({
  requestSuggestions: vi.fn(() => "requestSuggestionsTool"),
}));

vi.mock("@/lib/ai/tools/get-weather", () => ({
  getWeather: "getWeatherTool",
}));

vi.mock("@/lib/constants", () => ({
  isProductionEnvironment: false,
}));

vi.mock("@/lib/db/queries", () => ({
  createStreamId: vi.fn(),
  deleteChatById: vi.fn(),
  getChatById: vi.fn(async () => ({ id: "chat-1", userId: "user-1" })),
  getMessageCountByUserId: vi.fn(async () => 0),
  getMessagesByChatId: vi.fn(async () => []),
  saveChat: vi.fn(),
  saveMessages: vi.fn(),
  updateChatLastContextById: vi.fn(),
}));

vi.mock("@/lib/utils", () => ({
  convertToUIMessages: vi.fn(() => []),
  generateUUID: vi.fn(() => "stream-id"),
}));

vi.mock("@/app/(chat)/actions", () => ({
  generateTitleFromUserMessage: vi.fn(async () => "title"),
}));

describe("chat route MCP integration", () => {
  const createRequest = () =>
    new Request("http://localhost/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        id: "00000000-0000-0000-0000-000000000001",
        message: {
          id: "00000000-0000-0000-0000-000000000002",
          role: "user",
          parts: [{ type: "text", text: "Hello" }],
        },
        selectedChatModel: "chat-model",
        selectedVisibilityType: "private",
      }),
    });

  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();

    mockLoadMcpTools.mockResolvedValue({ clients: [], tools: {} });

    mockCreateUIMessageStream.mockImplementation(({ execute }) => {
      const dataStream = {
        write: vi.fn(),
        merge: vi.fn(),
      };

      execute({ writer: dataStream });

      return {
        pipeThrough: vi.fn(() => "mock-body"),
      };
    });
  });

  test("merges MCP tools with local tools", async () => {
    const close = vi.fn(async () => undefined);

    mockLoadMcpTools.mockResolvedValue({
      clients: [{ close }],
      tools: { remoteTool: { description: "remote" } },
    });

    mockStreamText.mockReturnValue({
      consumeStream: vi.fn(),
      toUIMessageStream: vi.fn(() => ({ pipeThrough: vi.fn() })),
    });

    const { POST } = await import("@/app/(chat)/api/chat/route");

    const response = await POST(createRequest());

    expect(response.status).toBe(200);
    expect(mockStreamText).toHaveBeenCalledTimes(1);

    const call = mockStreamText.mock.calls[0][0];

    expect(call.tools).toMatchObject({
      remoteTool: expect.anything(),
      getWeather: expect.anything(),
      createDocument: expect.anything(),
      updateDocument: expect.anything(),
      requestSuggestions: expect.anything(),
    });

    expect(call.experimental_activeTools.sort()).toEqual(
      Object.keys(call.tools).sort()
    );

    expect(close).toHaveBeenCalledTimes(1);
  });

  test("closes MCP clients when streamText throws", async () => {
    const close = vi.fn(async () => undefined);

    mockLoadMcpTools.mockResolvedValue({
      clients: [{ close }],
      tools: { remoteTool: {} },
    });

    mockStreamText.mockImplementation(() => {
      throw new Error("boom");
    });

    const { POST } = await import("@/app/(chat)/api/chat/route");

    const response = await POST(createRequest());

    expect(response.status).toBe(503);
    expect(close).toHaveBeenCalledTimes(1);
  });
});

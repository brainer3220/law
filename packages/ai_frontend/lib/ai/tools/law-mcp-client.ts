import { experimental_createMCPClient } from "ai";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const DEFAULT_BASE_URL =
  process.env.LAW_MCP_BASE_URL ?? "http://127.0.0.1:8000/mcp";

const CLIENT_NAME = "ai-frontend";

type McpClient = Awaited<ReturnType<typeof experimental_createMCPClient>>;
type McpToolMap = Awaited<ReturnType<McpClient["tools"]>>;
type McpTool = McpToolMap[string];
type McpToolExecuteResult = Awaited<ReturnType<McpTool["execute"]>>;

type ExtractedContent = {
  type?: string;
  text?: string;
};

function createTransport(baseUrl: string) {
  try {
    return new StreamableHTTPClientTransport(new URL(baseUrl));
  } catch (error) {
    throw new Error(`Invalid LAW_MCP_BASE_URL: ${baseUrl}`, { cause: error });
  }
}

function extractTextContent(result: McpToolExecuteResult): string | undefined {
  if (!result || typeof result !== "object" || !("content" in result)) {
    return undefined;
  }

  const { content } = result as { content?: ExtractedContent[] };

  if (!Array.isArray(content)) {
    return undefined;
  }

  for (const part of content) {
    if (part && part.type === "text" && typeof part.text === "string") {
      return part.text;
    }
  }

  return undefined;
}

function extractResultPayload(result: McpToolExecuteResult): unknown {
  if (!result || typeof result !== "object") {
    return undefined;
  }

  if ("toolResult" in result) {
    return (result as { toolResult: unknown }).toolResult;
  }

  if ("isError" in result && (result as { isError?: boolean }).isError) {
    const errorMessage =
      extractTextContent(result) ?? "Unknown MCP tool error";
    throw new Error(errorMessage);
  }

  const textPayload = extractTextContent(result);

  if (typeof textPayload === "string") {
    try {
      return JSON.parse(textPayload);
    } catch (error) {
      console.warn("Unable to parse MCP tool JSON output", {
        text: textPayload,
        error,
      });
      return textPayload;
    }
  }

  return result;
}

export async function callLawMcpTool<TResult>(
  toolName: string,
  args: Record<string, unknown>,
  { signal }: { signal?: AbortSignal } = {}
): Promise<TResult> {
  const client = await experimental_createMCPClient({
    name: CLIENT_NAME,
    transport: createTransport(DEFAULT_BASE_URL),
  });

  try {
    const tools = await client.tools();
    const tool = tools[toolName];

    if (!tool) {
      throw new Error(`MCP tool '${toolName}' is not available on the server`);
    }

    const executeOptions =
      (signal !== undefined
        ? ({ abortSignal: signal } as unknown)
        : (undefined as unknown)) as Parameters<McpTool["execute"]>[1];

    const result = await tool.execute(args, executeOptions);

    return extractResultPayload(result) as TResult;
  } finally {
    await client.close();
  }
}

export type LawMcpHit = {
  source: string | null;
  path: string | null;
  doc_id: string | null;
  title: string | null;
  score: number | null;
  snippet: string | null;
  line_no: number | null;
  page_index: number | null;
  page_total: number | null;
};

export type LawMcpHitsPayload = {
  hits: LawMcpHit[];
  count: number;
};

import "server-only";

import { experimental_createMCPClient } from "ai";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse";

export type McpClient = Awaited<ReturnType<typeof experimental_createMCPClient>>;

export type McpToolsResult = {
  clients: McpClient[];
  tools: Record<string, unknown>;
};

const parseArgs = (value?: string): string[] => {
  if (!value) {
    return [];
  }

  try {
    const parsed = JSON.parse(value);

    if (Array.isArray(parsed) && parsed.every((item) => typeof item === "string")) {
      return parsed;
    }
  } catch (error) {
    // fall back to whitespace splitting if JSON parsing fails
  }

  return value
    .split(/\s+/)
    .map((entry) => entry.trim())
    .filter(Boolean);
};

const logInitializationError = (transport: string, error: unknown) => {
  console.warn(`Unable to initialize MCP ${transport} transport`, error);
};

export async function loadMcpTools(): Promise<McpToolsResult> {
  const clients: McpClient[] = [];
  const mergedTools: Record<string, unknown> = {};

  const stdioCommand = process.env.MCP_STDIO_COMMAND?.trim();
  const httpUrl = process.env.MCP_HTTP_URL?.trim();
  const sseUrl = process.env.MCP_SSE_URL?.trim();

  const registerClient = async (initializer: () => Promise<McpClient>, label: string) => {
    try {
      const client = await initializer();
      clients.push(client);

      try {
        const toolSet = await client.tools();
        Object.assign(mergedTools, toolSet);
      } catch (error) {
        logInitializationError(`${label} tools`, error);
      }
    } catch (error) {
      logInitializationError(label, error);
    }
  };

  if (stdioCommand) {
    await registerClient(async () => {
      const transport = new StdioClientTransport({
        command: stdioCommand,
        args: parseArgs(process.env.MCP_STDIO_ARGS),
      });

      return experimental_createMCPClient({ transport });
    }, "stdio");
  }

  if (httpUrl) {
    await registerClient(async () => {
      const transport = new StreamableHTTPClientTransport(new URL(httpUrl));
      return experimental_createMCPClient({ transport });
    }, "http");
  }

  if (sseUrl) {
    await registerClient(async () => {
      const transport = new SSEClientTransport(new URL(sseUrl));
      return experimental_createMCPClient({ transport });
    }, "sse");
  }

  return { clients, tools: mergedTools };
}

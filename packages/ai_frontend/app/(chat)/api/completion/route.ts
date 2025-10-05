import { experimental_createMCPClient, streamText } from "ai";
import { openai } from "@ai-sdk/openai";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

export const runtime = "nodejs";

const DEFAULT_BASE_URL = "http://127.0.0.1:8000/mcp";

const TRANSPORT_ALIASES: Record<string, string> = {
  http: "streamable-http",
  "streamable-http": "streamable-http",
  sse: "sse",
  stdio: "stdio",
};

type McpClient = Awaited<ReturnType<typeof experimental_createMCPClient>>;
type McpToolMap = Awaited<ReturnType<McpClient["tools"]>>;

type CompletionRequestBody = {
  prompt: string;
};

function parseTransportList(): string[] {
  const configured = process.env.LAW_MCP_TRANSPORT ?? "streamable-http";
  const values = configured
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean)
    .map((entry) => TRANSPORT_ALIASES[entry] ?? entry);

  return Array.from(new Set(values));
}

function resolveBaseUrl(): URL {
  const base = process.env.LAW_MCP_BASE_URL ?? DEFAULT_BASE_URL;
  return new URL(base);
}

function resolveSseUrl(base: URL): URL {
  const override = process.env.LAW_MCP_SSE_URL;
  if (override) {
    return new URL(override);
  }

  const derived = new URL(base.toString());
  derived.pathname = derived.pathname.replace(/\/?$/, "/");
  derived.pathname = `${derived.pathname.replace(/mcp\/?$/, "")}sse`;
  return derived;
}

function parseArgs(rawArgs: string | undefined): string[] {
  if (!rawArgs) {
    return ["run", "law-mcp-server"];
  }

  return rawArgs
    .trim()
    .split(/\s+/)
    .map((value) => value.trim())
    .filter(Boolean);
}

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

  const transports = parseTransportList();

  const clients: McpClient[] = [];
  let closed = false;

  const closeAllClients = async () => {
    if (closed) {
      return;
    }

    closed = true;

    const results = await Promise.allSettled(
      clients.map((client) => client.close())
    );

    results.forEach((result, idx) => {
      if (result.status === "rejected") {
        console.error(
          `Failed to close client at index ${idx}:`,
          result.reason
        );
      }
    });
  };

  try {
    const baseUrl = resolveBaseUrl();
    const tools: McpToolMap = {};

    if (transports.includes("stdio")) {
      const command = process.env.LAW_MCP_STDIO_COMMAND ?? "uv";
      const args = parseArgs(process.env.LAW_MCP_STDIO_ARGS);

      const stdioTransport = new StdioClientTransport({
        command,
        args,
        env: {
          ...process.env,
          LAW_MCP_TRANSPORT: "stdio",
        },
      });

      const stdioClient = await experimental_createMCPClient({
        transport: stdioTransport,
      });

      clients.push(stdioClient);

      const toolset = await stdioClient.tools();
      for (const [name, tool] of Object.entries(toolset)) {
        if (!(name in tools)) {
          tools[name] = tool;
        }
      }
    }

    if (transports.includes("streamable-http")) {
      const httpUrl = process.env.LAW_MCP_HTTP_URL
        ? new URL(process.env.LAW_MCP_HTTP_URL)
        : baseUrl;

      const httpClient = await experimental_createMCPClient({
        transport: new StreamableHTTPClientTransport(httpUrl),
      });

      clients.push(httpClient);

      const toolset = await httpClient.tools();
      for (const [name, tool] of Object.entries(toolset)) {
        if (!(name in tools)) {
          tools[name] = tool;
        }
      }
    }

    if (transports.includes("sse")) {
      const sseUrl = resolveSseUrl(baseUrl);
      const sseClient = await experimental_createMCPClient({
        transport: new SSEClientTransport(sseUrl),
      });

      clients.push(sseClient);

      const toolset = await sseClient.tools();
      for (const [name, tool] of Object.entries(toolset)) {
        if (!(name in tools)) {
          tools[name] = tool;
        }
      }
    }

    if (clients.length === 0) {
      await closeAllClients();
      return new Response("No MCP transports configured", { status: 503 });
    }

    const response = await streamText({
      model: openai("gpt-4o"),
      prompt,
      tools,
      onFinish: async () => {
        await closeAllClients();
      },
      onError: async () => {
        await closeAllClients();
      },
    });

    return response.toDataStreamResponse();
  } catch (error) {
    await closeAllClients();
    console.error("/api/completion failed", error);
    return new Response("Internal Server Error", { status: 500 });
  }
}

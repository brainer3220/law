import { randomUUID } from "crypto";

const DEFAULT_BASE_URL =
  process.env.LAW_MCP_BASE_URL ?? "http://127.0.0.1:8000/mcp";

const PROTOCOL_VERSION = "2024-11-05";
const CLIENT_NAME = "ai-frontend";
const CLIENT_VERSION = process.env.VERCEL_GIT_COMMIT_SHA ?? "0.0.0";

type JsonRpcBase = {
  jsonrpc: "2.0";
};

type JsonRpcRequest = JsonRpcBase & {
  id?: string;
  method: string;
  params?: Record<string, unknown>;
};

type JsonRpcResponse = JsonRpcBase &
  (
    | {
        id: string | number | null;
        result: unknown;
      }
    | {
        id: string | number | null;
        error: {
          code: number;
          message: string;
          data?: unknown;
        };
      }
  );

type StreamableHttpResult =
  | {
      content?: Array<{ type: string; text?: string }>;
      structuredContent?: { result?: unknown };
      isError?: boolean;
    }
  | undefined;

type McpMessage = {
  id?: string | number | null;
  result?: StreamableHttpResult;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
};

type SendOptions = {
  sessionId?: string | null;
  signal?: AbortSignal;
};

type SendResult = {
  sessionId?: string | null;
  message?: McpMessage;
};

type HandshakeState = {
  sessionId: string | null;
  initialized: boolean;
  handshakePromise: Promise<void> | null;
};

const state: HandshakeState = {
  sessionId: null,
  initialized: false,
  handshakePromise: null,
};

function parseSseStream(raw: string): McpMessage | undefined {
  const blocks = raw
    .split(/\n\n+/)
    .map((block) => block.trim())
    .filter(Boolean);

  for (const block of blocks) {
    const lines = block.split(/\n/);
    let dataLines: string[] = [];
    for (const line of lines) {
      if (line.startsWith("data:")) {
        const value = line.slice("data:".length).trimStart();
        dataLines.push(value);
      }
    }

    if (dataLines.length === 0) {
      continue;
    }

    const data = dataLines.join("\n");

    try {
      const parsed = JSON.parse(data) as JsonRpcResponse;
      if ("result" in parsed || "error" in parsed) {
        return {
          id: parsed.id,
          result: (parsed as any).result,
          error: (parsed as any).error,
        };
      }
    } catch (error) {
      console.warn("Failed to parse MCP SSE payload", { data, error });
    }
  }

  return undefined;
}

async function sendRequest(
  payload: JsonRpcRequest,
  { sessionId, signal }: SendOptions
): Promise<SendResult> {
  const response = await fetch(DEFAULT_BASE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      ...(sessionId ? { "mcp-session-id": sessionId } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  const responseText = await response.text();
  const nextSessionId =
    response.headers.get("mcp-session-id") ?? sessionId ?? undefined;

  if (!response.ok) {
    const errorMessage =
      parseSseStream(responseText)?.error?.message ?? responseText;
    throw new Error(
      `MCP request failed with status ${response.status}: ${errorMessage}`
    );
  }

  return {
    sessionId: nextSessionId ?? null,
    message: parseSseStream(responseText),
  };
}

async function performHandshake(signal?: AbortSignal) {
  const payload: JsonRpcRequest = {
    jsonrpc: "2.0",
    id: randomUUID(),
    method: "initialize",
    params: {
      protocolVersion: PROTOCOL_VERSION,
      clientInfo: {
        name: CLIENT_NAME,
        version: CLIENT_VERSION,
      },
      capabilities: {},
    },
  };

  const { sessionId, message } = await sendRequest(payload, {
    signal,
  });

  if (!sessionId) {
    throw new Error("Law MCP server did not provide a session id");
  }

  state.sessionId = sessionId;

  if (message?.error) {
    throw new Error(
      `Failed to initialize MCP session: ${message.error.message}`
    );
  }

  await sendRequest(
    {
      jsonrpc: "2.0",
      method: "notifications/initialized",
    },
    { sessionId, signal }
  );

  state.initialized = true;
}

async function ensureSession(signal?: AbortSignal) {
  if (state.initialized && state.sessionId) {
    return;
  }

  if (!state.handshakePromise) {
    state.handshakePromise = performHandshake(signal).catch((error) => {
      state.sessionId = null;
      state.initialized = false;
      throw error;
    });
  }

  try {
    await state.handshakePromise;
  } finally {
    state.handshakePromise = null;
  }
}

function extractResult(message?: McpMessage): unknown {
  if (!message) {
    return undefined;
  }

  if (message.error) {
    throw new Error(message.error.message);
  }

  const result = message.result;

  if (!result) {
    return undefined;
  }

  if (result.isError) {
    const errorText = result.content?.[0]?.text ?? "Unknown MCP tool error";
    throw new Error(errorText);
  }

  if (result.structuredContent && "result" in result.structuredContent) {
    return result.structuredContent.result;
  }

  const textPayload = result.content?.[0]?.text;

  if (textPayload) {
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
  await ensureSession(signal);

  if (!state.sessionId) {
    throw new Error("Law MCP session is not available");
  }

  const request: JsonRpcRequest = {
    jsonrpc: "2.0",
    id: randomUUID(),
    method: "tools/call",
    params: {
      name: toolName,
      arguments: args,
    },
  };

  const { message } = await sendRequest(request, {
    sessionId: state.sessionId,
    signal,
  });

  return extractResult(message) as TResult;
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

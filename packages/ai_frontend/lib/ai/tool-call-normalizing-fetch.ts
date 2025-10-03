const DOUBLE_NEWLINE = "\n\n";

type FetchType = typeof fetch;

function coerceToolCallIndex(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function normalizeToolCallDelta(delta: unknown): boolean {
  if (!delta || typeof delta !== "object") {
    return false;
  }

  const draft = delta as Record<string, unknown>;
  const rawCalls = draft["tool_calls"];
  if (!Array.isArray(rawCalls) || rawCalls.length === 0) {
    return false;
  }

  let mutated = false;

  draft["tool_calls"] = rawCalls.map((call, idx) => {
    if (!call || typeof call !== "object") {
      mutated = true;
      return {
        index: idx,
        type: "function",
        function: { arguments: "" },
      };
    }

    const normalizedCall = { ...(call as Record<string, unknown>) };

    const numericIndex = coerceToolCallIndex(normalizedCall.index, idx);
    if (normalizedCall.index !== numericIndex) {
      mutated = true;
    }
    normalizedCall.index = numericIndex;

    if (normalizedCall.type == null) {
      normalizedCall.type = "function";
      mutated = true;
    }

    if (typeof normalizedCall.type !== "string") {
      normalizedCall.type = String(normalizedCall.type);
      mutated = true;
    }

    const fn = normalizedCall.function;
    if (!fn || typeof fn !== "object") {
      normalizedCall.function = { name: "", arguments: "" };
      mutated = true;
    } else {
      const normalizedFn = { ...(fn as Record<string, unknown>) };

      if (normalizedFn.name != null && typeof normalizedFn.name !== "string") {
        normalizedFn.name = String(normalizedFn.name);
        mutated = true;
      }

      if (normalizedFn.name == null) {
        normalizedFn.name = "";
        mutated = true;
      }

      const rawArguments = normalizedFn.arguments;
      if (rawArguments == null) {
        normalizedFn.arguments = "";
        mutated = true;
      } else if (typeof rawArguments !== "string") {
        try {
          normalizedFn.arguments = JSON.stringify(rawArguments);
        } catch {
          normalizedFn.arguments = String(rawArguments);
        }
        mutated = true;
      }

      normalizedCall.function = normalizedFn;
    }

    return normalizedCall;
  });

  return mutated;
}

function normalizeChunkPayload(payload: any): { mutated: boolean; value: any } {
  if (!payload || typeof payload !== "object") {
    return { mutated: false, value: payload };
  }

  if (!Array.isArray(payload.choices)) {
    return { mutated: false, value: payload };
  }

  let mutated = false;
  const nextChoices = payload.choices.map((choice: any) => {
    if (!choice || typeof choice !== "object") {
      return choice;
    }

    if (choice.delta && typeof choice.delta === "object") {
      const clonedDelta = { ...choice.delta };
      const deltaMutated = normalizeToolCallDelta(clonedDelta);
      if (deltaMutated) {
        mutated = true;
        return { ...choice, delta: clonedDelta };
      }
    }

    return choice;
  });

  if (!mutated) {
    return { mutated: false, value: payload };
  }

  return { mutated: true, value: { ...payload, choices: nextChoices } };
}

function rebuildEventLines(
  lines: string[],
  normalizedData: string
): string[] {
  const dataLines = normalizedData.split("\n").map((line) => `data: ${line}`);

  const preserved = lines.filter((line) => !line.startsWith("data:"));
  return [...preserved, ...dataLines];
}

function normalizeEventBlock(block: string): string {
  if (!block.trim()) {
    return block;
  }

  const lines = block.split("\n");
  const dataPayload = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice("data:".length).trimStart())
    .join("\n");

  if (!dataPayload) {
    return block;
  }

  let parsed: any;
  try {
    parsed = JSON.parse(dataPayload);
  } catch {
    return block;
  }

  const { mutated, value } = normalizeChunkPayload(parsed);
  if (!mutated) {
    return block;
  }

  const normalizedLines = rebuildEventLines(lines, JSON.stringify(value));
  return normalizedLines.join("\n");
}

function createNormalizedStream(
  body: ReadableStream<Uint8Array>
): ReadableStream<Uint8Array> {
  const reader = body.getReader();
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let buffer = "";

  const enqueueEvents = (
    controller: ReadableStreamDefaultController<Uint8Array>,
    flush: boolean
  ) => {
    let working = buffer;
    if (!working) {
      return;
    }

    if (!working.endsWith(DOUBLE_NEWLINE) && !flush) {
      const lastSeparator = working.lastIndexOf(DOUBLE_NEWLINE);
      if (lastSeparator === -1) {
        return;
      }
      const complete = working.slice(0, lastSeparator + DOUBLE_NEWLINE.length);
      const remainder = working.slice(lastSeparator + DOUBLE_NEWLINE.length);
      working = complete;
      buffer = remainder;
    } else {
      buffer = "";
    }

    const events = working.split(DOUBLE_NEWLINE);
    const tail = events.pop();
    const finalizedEvents = flush ? events.concat(tail ?? "") : events;

    for (const event of finalizedEvents) {
      if (!event) {
        continue;
      }
      const normalized = normalizeEventBlock(event);
      controller.enqueue(encoder.encode(`${normalized}\n\n`));
    }

    if (!flush && tail) {
      buffer = tail;
    }
  };

  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      const { value, done } = await reader.read();
      if (done) {
        buffer += decoder.decode();
        enqueueEvents(controller, true);
        controller.close();
        return;
      }

      buffer += decoder
        .decode(value, { stream: true })
        .replace(/\r\n/g, "\n");
      enqueueEvents(controller, false);
    },
    cancel(reason) {
      reader.cancel(reason).catch(() => {});
    },
  });
}

export function createToolCallNormalizingFetch(
  baseFetch: FetchType = fetch
): FetchType {
  return async function toolCallNormalizingFetch(input, init) {
    const response = await baseFetch(input, init);

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("text/event-stream")) {
      return response;
    }

    const body = response.body;
    if (!body) {
      return response;
    }

    const normalizedStream = createNormalizedStream(body);
    const headers = new Headers(response.headers);
    headers.delete("content-length");
    return new Response(normalizedStream, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  };
}


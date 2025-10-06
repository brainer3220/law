const DEFAULT_BASE_URL =
  process.env.LAW_TOOL_BASE_URL ??
  process.env.OPENAI_COMPATIBLE_BASE_URL ??
  "http://127.0.0.1:8080/v1";

function buildToolUrl(toolName: string): URL {
  const url = new URL(DEFAULT_BASE_URL);
  const basePath = url.pathname.replace(/\/?$/, "/");
  url.pathname = `${basePath}law/tools/${toolName}`;
  return url;
}

function extractErrorMessage(text: string): string | null {
  if (!text) {
    return null;
  }

  try {
    const parsed = JSON.parse(text);
    if (typeof parsed === "string") {
      return parsed;
    }
    if (parsed && typeof parsed === "object") {
      if (typeof (parsed as any).error === "string") {
        return (parsed as any).error as string;
      }
      if (typeof (parsed as any).message === "string") {
        return (parsed as any).message as string;
      }
    }
  } catch {
    // Ignore JSON parse failures; fall back to raw text
  }

  return text;
}

export async function callLawTool<TResult>(
  toolName: string,
  args: Record<string, unknown>,
  { signal }: { signal?: AbortSignal } = {}
): Promise<TResult> {
  const url = buildToolUrl(toolName);
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(args ?? {}),
    signal,
  });

  const text = await response.text();

  if (!response.ok) {
    const detail = extractErrorMessage(text);
    const message = detail
      ? `Law tool request failed with status ${response.status}: ${detail}`
      : `Law tool request failed with status ${response.status}`;
    throw new Error(message);
  }

  if (!text) {
    throw new Error("Law tool request returned an empty response");
  }

  try {
    return JSON.parse(text) as TResult;
  } catch (error) {
    console.warn("Unable to parse law tool JSON payload", { text, error });
    throw new Error("Law tool request returned malformed JSON");
  }
}

export type LawToolHit = {
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

export type LawToolHitsPayload = {
  hits: LawToolHit[];
  count: number;
};

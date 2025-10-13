const DEFAULT_SHARE_SERVICE_BASE = "http://127.0.0.1:8081";

export function resolveShareServiceBaseUrl(): string {
  const base = process.env.SHARE_SERVICE_BASE_URL ?? DEFAULT_SHARE_SERVICE_BASE;
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

export function buildShareServiceUrl(path: string): string {
  const base = resolveShareServiceBaseUrl();
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export interface ShareServiceRequestInit extends RequestInit {
  headers?: HeadersInit;
}

export async function callShareService(
  path: string,
  init?: ShareServiceRequestInit
): Promise<Response> {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }

  const apiKey = process.env.SHARE_SERVICE_API_KEY;
  if (apiKey && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${apiKey}`);
  }

  const url = buildShareServiceUrl(path);
  return fetch(url, {
    ...init,
    headers,
  });
}

export async function parseShareServiceJson<T>(response: Response): Promise<T> {
  const payload = (await response.json().catch(() => null)) as T | null;
  if (!response.ok || !payload) {
    const errorMessage =
      (payload as { error?: string } | null)?.error ??
      `Share service request failed with status ${response.status}`;
    throw new Error(errorMessage);
  }
  return payload;
}

export async function forwardShareServiceResponse(upstream: Response): Promise<Response> {
  const contentType =
    upstream.headers.get("content-type")?.split(";")[0].trim().toLowerCase() ??
    "application/json";
  const rawBody = await upstream.text();
  const body =
    rawBody && rawBody.length > 0
      ? rawBody
      : JSON.stringify({ error: upstream.statusText });

  const headers = new Headers({
    "Content-Type": contentType.includes("json")
      ? "application/json"
      : contentType,
  });

  return new Response(body, {
    status: upstream.status,
    headers,
  });
}

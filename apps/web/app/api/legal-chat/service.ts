const DEFAULT_LAW_API_BASE = "http://127.0.0.1:8080";

export function resolveLawApiBaseUrl(): string {
  const base = process.env.LAW_API_BASE_URL ?? DEFAULT_LAW_API_BASE;
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

export function buildLawApiUrl(path: string): string {
  const base = resolveLawApiBaseUrl();
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function callLawApi(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(buildLawApiUrl(path), {
    ...init,
    headers,
  });
}

export async function forwardLawApiResponse(upstream: Response): Promise<Response> {
  const contentType =
    upstream.headers.get("content-type")?.split(";")[0].trim().toLowerCase() ??
    "application/json";
  const body = await upstream.text();
  return new Response(body || JSON.stringify({ error: upstream.statusText }), {
    status: upstream.status,
    headers: {
      "Content-Type": contentType.includes("json")
        ? "application/json"
        : contentType,
    },
  });
}

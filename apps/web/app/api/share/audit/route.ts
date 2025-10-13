import { NextResponse } from "next/server";

import {
  callShareService,
  forwardShareServiceResponse,
} from "../../share/service";

export const runtime = "nodejs";

export async function GET(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const resourceId = url.searchParams.get("resourceId");
  const action = url.searchParams.get("action");

  if (!resourceId) {
    return NextResponse.json(
      { error: "resourceId query parameter is required" },
      { status: 400 }
    );
  }

  const query = new URLSearchParams({ resource_id: resourceId });
  if (action) {
    query.set("action", action);
  }

  try {
    const upstream = await callShareService(`/v1/audit?${query.toString()}`, {
      method: "GET",
    });
    return forwardShareServiceResponse(upstream);
  } catch (error) {
    console.error("[share] Failed to load audit logs", error);
    return NextResponse.json(
      { error: "Unable to fetch audit logs" },
      { status: 502 }
    );
  }
}

export async function POST(): Promise<Response> {
  return NextResponse.json({ error: "Not Implemented" }, { status: 405 });
}

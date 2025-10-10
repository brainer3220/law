import { NextResponse } from "next/server";

import {
  callShareService,
  forwardShareServiceResponse,
} from "../../../share/service";

export const runtime = "nodejs";

type RouteParams = {
  params: Promise<{
    shareId: string;
  }>;
};

export async function POST(request: Request, context: RouteParams): Promise<Response> {
  const params = await context.params;
  try {
    const body = await request.text();
    const upstream = await callShareService(`/v1/shares/${params.shareId}/revoke`, {
      method: "POST",
      body,
      headers: {
        "Content-Type": "application/json",
      },
    });
    return forwardShareServiceResponse(upstream);
  } catch (error) {
    console.error("[share] Failed to revoke share", error);
    return NextResponse.json({ error: "Unable to revoke share" }, { status: 502 });
  }
}

export async function GET(): Promise<Response> {
  return NextResponse.json({ error: "Not Implemented" }, { status: 405 });
}

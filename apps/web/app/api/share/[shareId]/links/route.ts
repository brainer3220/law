import { NextResponse } from "next/server";

import { requireAuthenticatedUserId } from "../../../auth/require-user";
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
    const userId = await requireAuthenticatedUserId();
    if (userId instanceof Response) {
      return userId;
    }
    const payload = (await request.json()) as Record<string, unknown>;
    payload.actor_id = userId;
    const upstream = await callShareService(`/v1/shares/${params.shareId}/links`, {
      method: "POST",
      body: JSON.stringify(payload),
      actorId: userId,
      headers: {
        "Content-Type": "application/json",
      },
    });
    return forwardShareServiceResponse(upstream);
  } catch (error) {
    console.error("[share] Failed to create share link", error);
    return NextResponse.json(
      { error: "Unable to create share link" },
      { status: 502 }
    );
  }
}

export async function GET(): Promise<Response> {
  return NextResponse.json({ error: "Not Implemented" }, { status: 405 });
}

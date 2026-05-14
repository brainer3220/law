import { NextResponse } from "next/server";

import { requireAuthenticatedUserId } from "../auth/require-user";
import { callShareService, forwardShareServiceResponse } from "./service";

export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  try {
    const userId = await requireAuthenticatedUserId();
    if (userId instanceof Response) {
      return userId;
    }
    const payload = (await request.json()) as Record<string, unknown>;
    payload.actor_id = userId;
    const upstream = await callShareService("/v1/shares", {
      method: "POST",
      body: JSON.stringify(payload),
      actorId: userId,
      headers: {
        "Content-Type": "application/json",
      },
    });
    return forwardShareServiceResponse(upstream);
  } catch (error) {
    console.error("[share] Failed to create share", error);
    return NextResponse.json(
      { error: "Unable to reach share service" },
      { status: 502 }
    );
  }
}

export async function GET(): Promise<Response> {
  return NextResponse.json({ error: "Not Implemented" }, { status: 405 });
}

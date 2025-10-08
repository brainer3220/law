import { NextResponse } from "next/server";

import {
  callShareService,
  forwardShareServiceResponse,
} from "../../share/service";

export const runtime = "nodejs";

type RouteParams = {
  params: {
    shareId: string;
  };
};

export async function GET(_: Request, { params }: RouteParams): Promise<Response> {
  try {
    const upstream = await callShareService(`/v1/shares/${params.shareId}`, {
      method: "GET",
    });
    return forwardShareServiceResponse(upstream);
  } catch (error) {
    console.error("[share] Failed to load share", error);
    return NextResponse.json(
      { error: "Unable to fetch share from service" },
      { status: 502 }
    );
  }
}

export async function POST(): Promise<Response> {
  return NextResponse.json({ error: "Not Implemented" }, { status: 405 });
}

export async function PUT(): Promise<Response> {
  return NextResponse.json({ error: "Not Implemented" }, { status: 405 });
}

export async function DELETE(): Promise<Response> {
  return NextResponse.json({ error: "Not Implemented" }, { status: 405 });
}

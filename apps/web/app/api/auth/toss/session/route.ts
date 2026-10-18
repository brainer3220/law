import { NextResponse } from "next/server";

import { getTossSession } from "@/lib/toss/tossAuth";

export async function GET() {
  const session = await getTossSession();
  if (!session) {
    return NextResponse.json({ authenticated: false });
  }
  return NextResponse.json({ authenticated: true, userKey: session.userKey, provider: session.provider });
}

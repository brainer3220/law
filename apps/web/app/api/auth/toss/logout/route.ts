import { NextResponse } from "next/server";

import { clearTossSession } from "@/lib/toss/tossAuth";

export async function POST() {
  await clearTossSession();
  return NextResponse.json({ ok: true });
}

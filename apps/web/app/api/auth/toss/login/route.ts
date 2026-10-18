import { NextResponse } from "next/server";

import { exchangeTossAuthorizationCode, setTossSession } from "@/lib/toss/tossAuth";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { authorizationCode?: string; referrer?: string };
    if (!body.authorizationCode || !body.referrer) {
      return NextResponse.json({ error: "authorizationCode와 referrer가 필요해요." }, { status: 400 });
    }
    const session = await exchangeTossAuthorizationCode({
      authorizationCode: body.authorizationCode,
      referrer: body.referrer as "DEFAULT" | "SANDBOX" | "sandbox",
    });
    await setTossSession(session);
    return NextResponse.json({ ok: true, userKey: session.userKey });
  } catch (error) {
    const message = error instanceof Error ? error.message : "토스 로그인에 실패했어요";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}

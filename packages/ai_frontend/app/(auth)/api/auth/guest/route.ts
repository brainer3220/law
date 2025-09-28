import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { isDevelopmentEnvironment } from "@/lib/constants";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const redirectParam = requestUrl.searchParams.get("redirectUrl");
  let safeRedirect = "/";

  if (redirectParam) {
    if (redirectParam.startsWith("/")) {
      safeRedirect = redirectParam;
    } else {
      try {
        const parsed = new URL(redirectParam, requestUrl);
        if (parsed.origin === requestUrl.origin) {
          safeRedirect = `${parsed.pathname}${parsed.search}`;
        }
      } catch {
        // Ignore malformed URLs and fall back to default
      }
    }
  }

  const token = await getToken({
    req: request,
    secret: process.env.AUTH_SECRET,
    secureCookie: !isDevelopmentEnvironment,
  });

  if (token) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  const loginUrl = new URL(
    `/login?redirectUrl=${encodeURIComponent(safeRedirect)}`,
    request.url
  );
  return NextResponse.redirect(loginUrl);
}

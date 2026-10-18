import crypto from "node:crypto";
import https from "node:https";

import { cookies } from "next/headers";

const TOSS_API_BASE_URL = "https://apps-in-toss-api.toss.im";
const TOSS_SESSION_COOKIE = "law_toss_session";
const TOSS_SESSION_MAX_AGE_SECONDS = 14 * 24 * 60 * 60;

export type TossSession = {
  provider: "toss";
  userKey: string;
  scope?: string;
  referrer?: "DEFAULT" | "SANDBOX" | "sandbox";
  createdAt: number;
};

type TossTokenSuccess = {
  accessToken: string;
  refreshToken?: string;
  scope?: string;
  tokenType?: string;
  expiresIn?: number | string;
};

type TossLoginMeSuccess = {
  userKey: number | string;
  scope?: string;
  agreedTerms?: string[];
  name?: string | null;
  email?: string | null;
};

export async function exchangeTossAuthorizationCode(input: {
  authorizationCode: string;
  referrer: "DEFAULT" | "SANDBOX" | "sandbox";
}): Promise<TossSession> {
  const tokenPayload = await tossApi<TossTokenSuccess>("/api-partner/v1/apps-in-toss/user/oauth2/generate-token", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(input),
  });
  const profile = await tossApi<TossLoginMeSuccess>("/api-partner/v1/apps-in-toss/user/oauth2/login-me", {
    method: "GET",
    headers: { authorization: `Bearer ${tokenPayload.accessToken}` },
  });
  if (profile.userKey === null || profile.userKey === undefined || String(profile.userKey).trim() === "") {
    throw new Error("토스 로그인 응답에 userKey가 없어요.");
  }
  return {
    provider: "toss",
    userKey: String(profile.userKey),
    scope: profile.scope ?? tokenPayload.scope,
    referrer: input.referrer,
    createdAt: Date.now(),
  };
}

export async function getTossSession(): Promise<TossSession | null> {
  const cookie = (await cookies()).get(TOSS_SESSION_COOKIE)?.value;
  return cookie ? verifySessionCookie(cookie) : null;
}

export async function setTossSession(session: TossSession) {
  (await cookies()).set(TOSS_SESSION_COOKIE, signSessionCookie(session), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: TOSS_SESSION_MAX_AGE_SECONDS,
  });
}

export async function clearTossSession() {
  (await cookies()).delete(TOSS_SESSION_COOKIE);
}

function signSessionCookie(session: TossSession) {
  const payload = Buffer.from(JSON.stringify(session)).toString("base64url");
  return `${payload}.${signatureFor(payload)}`;
}

function verifySessionCookie(value: string): TossSession | null {
  const [payload, signature] = value.split(".");
  if (!payload || !signature || !hasValidSignature(payload, signature)) {
    return null;
  }
  try {
    const session = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as TossSession;
    if (session.provider !== "toss" || !session.userKey || !session.createdAt) {
      return null;
    }
    if (Date.now() - session.createdAt > TOSS_SESSION_MAX_AGE_SECONDS * 1000) {
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

function signatureFor(payload: string) {
  return crypto.createHmac("sha256", sessionSecret()).update(payload).digest("base64url");
}

function hasValidSignature(payload: string, signature: string) {
  const expected = signatureFor(payload);
  const actualBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);
  return actualBuffer.length === expectedBuffer.length && crypto.timingSafeEqual(actualBuffer, expectedBuffer);
}

function sessionSecret() {
  const secret = process.env.TOSS_LOGIN_SESSION_SECRET;
  if (!secret) {
    throw new Error("TOSS_LOGIN_SESSION_SECRET이 필요해요.");
  }
  return secret;
}

async function tossApi<T>(path: string, init: RequestInit): Promise<T> {
  const response = await tossApiRequest(path, init);
  const payload = parseJsonResponse(response.body);
  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw new Error(`토스 로그인 API 요청에 실패했어요. HTTP ${response.statusCode}`);
  }
  if (!isRecord(payload)) {
    throw new Error("토스 로그인 API 응답이 올바르지 않아요.");
  }
  if (payload.resultType === "SUCCESS" && isRecord(payload.success)) {
    return payload.success as T;
  }
  if ("accessToken" in payload || "userKey" in payload) {
    return payload as T;
  }
  const message =
    (isRecord(payload.error) && typeof payload.error.reason === "string" && payload.error.reason) ||
    (typeof payload.error === "string" && payload.error) ||
    "토스 로그인 API가 실패를 반환했어요.";
  throw new Error(message);
}

function parseJsonResponse(body: string) {
  if (!body) {
    return null;
  }
  try {
    return JSON.parse(body) as unknown;
  } catch {
    return null;
  }
}

function tossApiRequest(path: string, init: RequestInit): Promise<{ statusCode: number; body: string }> {
  const url = new URL(path, TOSS_API_BASE_URL);
  const body = typeof init.body === "string" ? init.body : undefined;
  const headers = new Headers(init.headers);
  if (body && !headers.has("content-length")) {
    headers.set("content-length", Buffer.byteLength(body, "utf8").toString());
  }

  return new Promise<{ statusCode: number; body: string }>((resolve, reject) => {
    const request = https.request(
      url,
      {
        method: init.method,
        cert: tossMtlsCertificate(),
        key: tossMtlsPrivateKey(),
        passphrase: process.env.TOSS_MTLS_KEY_PASSPHRASE,
        rejectUnauthorized: true,
        timeout: 5000,
        headers: Object.fromEntries(headers.entries()),
      },
      (response) => {
        const chunks: Buffer[] = [];
        response.on("data", (chunk) => {
          chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
        });
        response.on("end", () => {
          resolve({
            statusCode: response.statusCode ?? 0,
            body: Buffer.concat(chunks).toString("utf8"),
          });
        });
      },
    );
    request.on("timeout", () => {
      request.destroy(new Error("토스 로그인 API 요청 시간이 초과됐어요."));
    });
    request.on("error", (error) => {
      reject(error);
    });
    if (body) {
      request.write(body);
    }
    request.end();
  }).catch((error) => {
    if (error instanceof Error && error.message.includes("TOSS_MTLS")) {
      throw error;
    }
    throw new Error(
      `토스 로그인 API에 연결하지 못했어요. mTLS 인증서 설정을 확인해 주세요. (${error instanceof Error ? error.message : "네트워크 오류"})`,
    );
  });
}

function tossMtlsCertificate() {
  return requiredPemEnv("TOSS_MTLS_CERT_PEM", "TOSS_MTLS_CERT_BASE64");
}

function tossMtlsPrivateKey() {
  return requiredPemEnv("TOSS_MTLS_KEY_PEM", "TOSS_MTLS_KEY_BASE64");
}

function requiredPemEnv(rawName: string, base64Name: string) {
  const value = process.env[rawName] || decodeBase64Env(process.env[base64Name]);
  if (!value) {
    throw new Error(`${rawName} 또는 ${base64Name}이 필요해요.`);
  }
  return value.replace(/\\n/g, "\n");
}

function decodeBase64Env(value: string | undefined) {
  return value ? Buffer.from(value, "base64").toString("utf8") : "";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

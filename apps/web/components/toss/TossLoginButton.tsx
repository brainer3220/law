"use client";

import { useEffect, useState } from "react";

type RuntimeState = "checking" | "available" | "unavailable";

/**
 * Apps-in-Toss 로그인 버튼.
 * 토스/샌드박스 런타임에서만 렌더링된다. 일반 웹에서는 아무것도 보여주지 않는다
 * (일반 웹 로그인은 기존 Supabase 인증이 담당).
 */
export function TossLoginButton({ initialUserKey }: { initialUserKey?: string }) {
  const runtime = useAppsInTossRuntime();
  const [userKey, setUserKey] = useState(initialUserKey);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  if (runtime !== "available") {
    return null;
  }

  async function handleLogin() {
    setStatus("loading");
    setErrorMessage("");
    try {
      const { appLogin } = await import("@apps-in-toss/web-bridge");
      const { authorizationCode, referrer } = await appLogin();
      const response = await fetch("/api/auth/toss/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ authorizationCode, referrer }),
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { error?: string } | null;
        throw new Error(payload?.error ?? "토스 로그인에 실패했어요");
      }
      const payload = (await response.json()) as { userKey?: string };
      setUserKey(payload.userKey);
      window.location.reload();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "토스 로그인에 실패했어요");
      setStatus("error");
    }
  }

  async function handleLogout() {
    await fetch("/api/auth/toss/logout", { method: "POST" });
    setUserKey(undefined);
    window.location.reload();
  }

  if (userKey) {
    return (
      <div className="auth-actions" aria-label="로그인 상태">
        <span>토스 사용자 {userKey}</span>
        <button type="button" onClick={handleLogout}>
          로그아웃
        </button>
      </div>
    );
  }

  return (
    <>
      <button type="button" onClick={handleLogin} disabled={status === "loading"}>
        {status === "loading" ? "토스 로그인 중" : status === "error" ? "토스 로그인 재시도" : "토스 로그인"}
      </button>
      {errorMessage ? <span role="alert">{errorMessage}</span> : null}
    </>
  );
}

function useAppsInTossRuntime(): RuntimeState {
  const [runtime, setRuntime] = useState<RuntimeState>("checking");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { getOperationalEnvironment } = await import("@apps-in-toss/web-bridge");
        const environment = getOperationalEnvironment();
        if (!cancelled) {
          setRuntime(environment === "toss" || environment === "sandbox" ? "available" : "unavailable");
        }
      } catch {
        if (!cancelled) {
          setRuntime("unavailable");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return runtime;
}

"use client";

import { useCallback } from "react";
import { ChatKitPanel, type FactAction } from "@/components/ChatKitPanel";
import { useColorScheme } from "@/hooks/useColorScheme";
import { UserMenu } from "@/components/auth/UserMenu";
import Link from "next/link";

export default function App() {
  const { scheme, setScheme } = useColorScheme();

  const handleWidgetAction = useCallback(async (action: FactAction) => {
    if (process.env.NODE_ENV !== "production") {
      console.info("[ChatKitPanel] widget action", action);
    }
  }, []);

  const handleResponseEnd = useCallback(() => {
    if (process.env.NODE_ENV !== "production") {
      console.debug("[ChatKitPanel] response end");
    }
  }, []);

  return (
    <main className="flex min-h-screen flex-col bg-slate-100 dark:bg-slate-950">
      {/* Header with User Menu */}
      <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-6">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              법률 AI 에이전트
            </h1>
            <nav className="flex items-center gap-4">
              <Link
                href="/"
                className="text-sm font-medium text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
              >
                채팅
              </Link>
              <Link
                href="/workspace"
                className="text-sm font-medium text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
              >
                프로젝트
              </Link>
            </nav>
          </div>
          <UserMenu />
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 items-center justify-center px-6 py-6">
        <div className="mx-auto w-full max-w-5xl">
          <ChatKitPanel
            theme={scheme}
            onWidgetAction={handleWidgetAction}
            onResponseEnd={handleResponseEnd}
            onThemeRequest={setScheme}
          />
        </div>
      </div>
    </main>
  );
}

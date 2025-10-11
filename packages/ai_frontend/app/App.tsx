"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChatKitPanel, type FactAction } from "@/components/ChatKitPanel";
import { useColorScheme } from "@/hooks/useColorScheme";
import { UserMenu } from "@/components/auth/UserMenu";
import {
  ChatBubbleLeftRightIcon,
  FolderIcon,
} from "@heroicons/react/24/outline";

export default function App() {
  const { scheme, setScheme } = useColorScheme();
  const router = useRouter();

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
    <main className="material-app-shell">
      <header className="material-app-shell__bar">
        <div className="material-app-shell__headline">법률 AI 에이전트</div>
        <nav className="material-app-shell__nav" aria-label="주요 화면">
          <button
            type="button"
            className="material-icon-button"
            aria-label="채팅"
            onClick={() => router.push("/")}
          >
            <ChatBubbleLeftRightIcon className="material-icon" aria-hidden="true" />
          </button>
          <button
            type="button"
            className="material-icon-button"
            aria-label="프로젝트"
            onClick={() => router.push("/workspace")}
          >
            <FolderIcon className="material-icon" aria-hidden="true" />
          </button>
        </nav>
        <UserMenu />
      </header>

      <div className="material-app-shell__content">
        <div className="material-app-shell__canvas">
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

"use client";

import "@material/web/button/elevated-button.js";
import "@material/web/button/filled-tonal-button.js";
import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChatKitPanel, type FactAction } from "@/components/ChatKitPanel";
import { useColorScheme } from "@/hooks/useColorScheme";
import { UserMenu } from "@/components/auth/UserMenu";

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
        <nav className="material-app-shell__nav">
          <md-filled-tonal-button
            type="button"
            onClick={() => router.push("/")}
          >
            채팅
          </md-filled-tonal-button>
          <md-filled-tonal-button
            type="button"
            onClick={() => router.push("/workspace")}
          >
            프로젝트
          </md-filled-tonal-button>
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

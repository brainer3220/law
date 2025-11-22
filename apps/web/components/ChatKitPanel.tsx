"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import {
  STARTER_PROMPTS,
  PLACEHOLDER_INPUT,
  GREETING,
  CREATE_SESSION_ENDPOINT,
  WORKFLOW_ID,
} from "@/lib/config";
import { ErrorOverlay } from "./ErrorOverlay";
import type { ColorScheme } from "@/hooks/useColorScheme";
import { SharePanel } from "./SharePanel";

export type FactAction = {
  type: "save";
  factId: string;
  factText: string;
};

type ChatKitPanelProps = {
  theme: ColorScheme;
  onWidgetAction: (action: FactAction) => Promise<void>;
  onResponseEnd: () => void;
  onThemeRequest: (scheme: ColorScheme) => void;
};

type LoadingPhase = 'script' | 'session' | 'ready';

type ErrorType = 'network' | 'config' | 'auth' | 'unknown';

type ErrorState = {
  script: string | null;
  session: string | null;
  integration: string | null;
  retryable: boolean;
  type?: ErrorType;
};

const isBrowser = typeof window !== "undefined";
const isDev = process.env.NODE_ENV !== "production";

const createInitialErrors = (): ErrorState => ({
  script: null,
  session: null,
  integration: null,
  retryable: false,
});

const getLoadingMessage = (phase: LoadingPhase): string => {
  switch (phase) {
    case 'script':
      return '법률 AI 에이전트를 준비하고 있습니다...';
    case 'session':
      return '안전한 세션을 생성하고 있습니다...';
    case 'ready':
      return '거의 완료되었습니다...';
  }
};

const detectErrorType = (error: string): ErrorType => {
  if (error.includes('NEXT_PUBLIC_CHATKIT_WORKFLOW_ID')) return 'config';
  if (error.includes('Failed to create') || error.includes('fetch')) return 'network';
  if (error.includes('Unauthorized') || error.includes('client_secret')) return 'auth';
  return 'unknown';
};

export function ChatKitPanel({
  theme,
  onWidgetAction,
  onResponseEnd,
  onThemeRequest,
}: ChatKitPanelProps) {
  const processedFacts = useRef(new Set<string>());
  const [errors, setErrors] = useState<ErrorState>(() => createInitialErrors());
  const [isInitializingSession, setIsInitializingSession] = useState(true);
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>('script');
  const isMountedRef = useRef(true);
  const [scriptStatus, setScriptStatus] = useState<
    "pending" | "ready" | "error"
  >(() =>
    isBrowser && window.customElements?.get("openai-chatkit")
      ? "ready"
      : "pending"
  );
  const [widgetInstanceKey, setWidgetInstanceKey] = useState(0);
  const [sharePanelOpen, setSharePanelOpen] = useState(false);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  const setErrorState = useCallback((updates: Partial<ErrorState>) => {
    setErrors((current) => ({ ...current, ...updates }));
  }, []);

  useEffect(() => {
    console.log('🎨 ChatKitPanel mounted', {
      theme,
      workflowId: WORKFLOW_ID,
      scriptStatus,
      isBrowser
    });

    return () => {
      console.log('🎨 ChatKitPanel unmounting');
      isMountedRef.current = false;
    };
  }, [theme, scriptStatus]);

  useEffect(() => {
    console.log('🔄 ChatKitPanel script status:', scriptStatus);

    if (!isBrowser) {
      console.warn('⚠️ Not in browser environment');
      return;
    }

    let timeoutId: number | undefined;

    const handleLoaded = () => {
      if (!isMountedRef.current) {
        return;
      }
      setScriptStatus("ready");
      setLoadingPhase('session');
      setErrorState({ script: null });
    };

    const handleError = (event: Event) => {
      console.error("Failed to load chatkit.js for some reason", event);
      if (!isMountedRef.current) {
        return;
      }
      setScriptStatus("error");
      const detail = (event as CustomEvent<unknown>)?.detail ?? "unknown error";
      const errorMsg = `Error: ${detail}`;
      setErrorState({
        script: errorMsg,
        retryable: false,
        type: detectErrorType(errorMsg)
      });
      setIsInitializingSession(false);
    };

    window.addEventListener("chatkit-script-loaded", handleLoaded);
    window.addEventListener(
      "chatkit-script-error",
      handleError as EventListener
    );

    if (window.customElements?.get("openai-chatkit")) {
      handleLoaded();
    } else if (scriptStatus === "pending") {
      timeoutId = window.setTimeout(() => {
        if (!window.customElements?.get("openai-chatkit")) {
          handleError(
            new CustomEvent("chatkit-script-error", {
              detail:
                "ChatKit web component is unavailable. Verify that the script URL is reachable.",
            })
          );
        }
      }, 5000);
    }

    return () => {
      window.removeEventListener("chatkit-script-loaded", handleLoaded);
      window.removeEventListener(
        "chatkit-script-error",
        handleError as EventListener
      );
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [scriptStatus, setErrorState]);

  const isWorkflowConfigured = Boolean(
    WORKFLOW_ID && !WORKFLOW_ID.startsWith("wf_replace")
  );

  useEffect(() => {
    if (!isWorkflowConfigured && isMountedRef.current) {
      setErrorState({
        session: "Set NEXT_PUBLIC_CHATKIT_WORKFLOW_ID in your .env.local file.",
        retryable: false,
      });
      setIsInitializingSession(false);
    }
  }, [isWorkflowConfigured, setErrorState]);

  const handleResetChat = useCallback(() => {
    processedFacts.current.clear();
    if (isBrowser) {
      setScriptStatus(
        window.customElements?.get("openai-chatkit") ? "ready" : "pending"
      );
    }
    setIsInitializingSession(true);
    setErrors(createInitialErrors());
    setWidgetInstanceKey((prev) => prev + 1);
    setSharePanelOpen(false);
  }, []);

  const handleToggleSharePanel = useCallback(() => {
    if (!activeThreadId) {
      setSharePanelOpen(false);
      return;
    }
    setSharePanelOpen((current) => !current);
  }, [activeThreadId]);

  const getClientSecret = useCallback(
    async (currentSecret: string | null) => {
      if (isDev) {
        console.info("[ChatKitPanel] getClientSecret invoked", {
          currentSecretPresent: Boolean(currentSecret),
          workflowId: WORKFLOW_ID,
          endpoint: CREATE_SESSION_ENDPOINT,
        });
      }

      if (!isWorkflowConfigured) {
        const detail =
          "Set NEXT_PUBLIC_CHATKIT_WORKFLOW_ID in your .env.local file.";
        if (isMountedRef.current) {
          setErrorState({ session: detail, retryable: false });
          setIsInitializingSession(false);
        }
        throw new Error(detail);
      }

      if (isMountedRef.current) {
        if (!currentSecret) {
          setIsInitializingSession(true);
        }
        setErrorState({ session: null, integration: null, retryable: false });
      }

      try {
        const response = await fetch(CREATE_SESSION_ENDPOINT, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            workflow: { id: WORKFLOW_ID },
          }),
        });

        const raw = await response.text();

        if (isDev) {
          console.info("[ChatKitPanel] createSession response", {
            status: response.status,
            ok: response.ok,
            bodyPreview: raw.slice(0, 1600),
          });
        }

        let data: Record<string, unknown> = {};
        if (raw) {
          try {
            data = JSON.parse(raw) as Record<string, unknown>;
          } catch (parseError) {
            console.error(
              "Failed to parse create-session response",
              parseError
            );
          }
        }

        if (!response.ok) {
          const detail = extractErrorDetail(data, response.statusText);
          console.error("Create session request failed", {
            status: response.status,
            body: data,
          });
          throw new Error(detail);
        }

        const clientSecret = data?.client_secret as string | undefined;
        if (!clientSecret) {
          throw new Error("Missing client secret in response");
        }

        if (isDev) {
          console.info("[ChatKitPanel] ✅ Successfully got client_secret, clearing errors");
        }

        if (isMountedRef.current) {
          setErrorState({ session: null, integration: null });
        }

        if (isDev) {
          console.info("[ChatKitPanel] Returning client_secret to ChatKit");
        }

        // Clear initializing state on successful secret retrieval
        if (isMountedRef.current) {
          setLoadingPhase('ready');
          setIsInitializingSession(false);
        }

        return clientSecret;
      } catch (error) {
        console.error("Failed to create ChatKit session", error);
        const detail =
          error instanceof Error
            ? error.message
            : "Unable to start ChatKit session.";
        if (isMountedRef.current) {
          setErrorState({
            session: detail,
            retryable: false,
            type: detectErrorType(detail)
          });
          setIsInitializingSession(false);
        }
        throw error instanceof Error ? error : new Error(detail);
      }
    },
    [isWorkflowConfigured, setErrorState]
  );

  // Memoize ChatKit configuration to prevent unnecessary re-creation
  const chatkitConfig = useMemo(() => ({
    api: { getClientSecret },
    theme: {
      colorScheme: theme,
      color: {
        grayscale: {
          hue: 220 as const,
          tint: 6 as const,
          shade: theme === "dark" ? (-1 as const) : (-4 as const),
        },
        accent: {
          primary: theme === "dark" ? "#f1f5f9" : "#0f172a",
          level: 1 as const,
        },
      },
      radius: "round" as const,
    },
    header: {
      enabled: true,
      rightAction: activeThreadId
        ? {
          icon: sharePanelOpen
            ? "sidebar-collapse-right" as const
            : "sidebar-open-right" as const,
          onClick: handleToggleSharePanel,
        }
        : undefined,
    },
    startScreen: {
      greeting: GREETING,
      prompts: STARTER_PROMPTS,
    },
    composer: {
      placeholder: PLACEHOLDER_INPUT,
    },
    threadItemActions: {
      feedback: false,
    },
    onClientTool: async (invocation: {
      name: string;
      params: Record<string, unknown>;
    }) => {
      if (invocation.name === "switch_theme") {
        const requested = invocation.params.theme;
        if (requested === "light" || requested === "dark") {
          if (isDev) {
            console.debug("[ChatKitPanel] switch_theme", requested);
          }
          onThemeRequest(requested);
          return { success: true };
        }
        return { success: false };
      }

      if (invocation.name === "record_fact") {
        const id = String(invocation.params.fact_id ?? "");
        const text = String(invocation.params.fact_text ?? "");
        if (!id || processedFacts.current.has(id)) {
          return { success: true };
        }
        processedFacts.current.add(id);
        void onWidgetAction({
          type: "save",
          factId: id,
          factText: text.replace(/\s+/g, " ").trim(),
        });
        return { success: true };
      }

      return { success: false };
    },
    onResponseEnd: () => {
      onResponseEnd();
    },
    onResponseStart: () => {
      setErrorState({ integration: null, retryable: false });
    },
    onThreadChange: ({ threadId }: { threadId: string | null }) => {
      processedFacts.current.clear();
      setSharePanelOpen(false);
      setActiveThreadId(threadId ?? null);
    },
    onThreadLoadEnd: ({ threadId }: { threadId: string }) => {
      setActiveThreadId(threadId);
    },
    onError: ({ error }: { error: unknown }) => {
      // Note that Chatkit UI handles errors for your users.
      // Thus, your app code doesn't need to display errors on UI.
      console.error("ChatKit error", error);
    },
  }), [
    getClientSecret,
    theme,
    activeThreadId,
    sharePanelOpen,
    handleToggleSharePanel,
    onThemeRequest,
    onWidgetAction,
    onResponseEnd,
    setErrorState,
  ]);

  const chatkit = useChatKit(chatkitConfig);

  // Track when ChatKit control becomes available
  useEffect(() => {
    if (chatkit.control) {
      if (isDev) {
        console.info("🎉 ChatKit control is now available! Session initialized successfully.");
      }
      // Control is ready, so we should clear the initializing state
      setIsInitializingSession(false);
    }
  }, [chatkit.control]);

  const activeError = errors.session ?? errors.integration;
  const blockingError = errors.script ?? activeError;

  if (isDev) {
    console.debug("[ChatKitPanel] render state", {
      isInitializingSession,
      hasControl: Boolean(chatkit.control),
      scriptStatus,
      hasError: Boolean(blockingError),
      workflowId: WORKFLOW_ID,
    });
  }

  return (
    <div
      role="region"
      aria-label="법률 AI 에이전트 채팅"
      aria-live="polite"
      aria-busy={isInitializingSession}
      className="relative flex h-[calc(100vh-4rem)] sm:h-[85vh] lg:h-[90vh] w-full flex-col overflow-hidden bg-white shadow-sm transition-all duration-300 ease-in-out dark:bg-slate-900"
    >
      {/* Screen reader announcements */}
      <div className="sr-only" aria-live="assertive" aria-atomic="true">
        {isInitializingSession && getLoadingMessage(loadingPhase)}
        {blockingError && `오류 발생: ${blockingError}`}
      </div>

      <ChatKit
        key={widgetInstanceKey}
        control={chatkit.control}
        className={
          blockingError || isInitializingSession
            ? "pointer-events-none opacity-0 scale-95 transition-all duration-500 ease-out"
            : "block h-full w-full opacity-100 scale-100 transition-all duration-500 ease-out"
        }
      />
      <ErrorOverlay
        error={blockingError}
        errorType={errors.type}
        fallbackMessage={
          blockingError || !isInitializingSession
            ? null
            : getLoadingMessage(loadingPhase)
        }
        onRetry={blockingError && errors.retryable ? handleResetChat : null}
        retryLabel="채팅 다시 시작"
      />

      {/* Backdrop when SharePanel is open */}
      {sharePanelOpen && Boolean(activeThreadId) && (
        <div
          className="absolute inset-0 bg-black/20 backdrop-blur-sm transition-opacity duration-300 z-40 animate-in fade-in"
          onClick={handleToggleSharePanel}
          aria-hidden="true"
        />
      )}

      <SharePanel
        open={sharePanelOpen && Boolean(activeThreadId)}
        onClose={handleToggleSharePanel}
        threadId={activeThreadId}
      />
    </div>
  );
}

function extractErrorDetail(
  payload: Record<string, unknown> | undefined,
  fallback: string
): string {
  if (!payload) {
    return fallback;
  }

  const error = payload.error;
  if (typeof error === "string") {
    return error;
  }

  if (
    error &&
    typeof error === "object" &&
    "message" in error &&
    typeof (error as { message?: unknown }).message === "string"
  ) {
    return (error as { message: string }).message;
  }

  const details = payload.details;
  if (typeof details === "string") {
    return details;
  }

  if (details && typeof details === "object" && "error" in details) {
    const nestedError = (details as { error?: unknown }).error;
    if (typeof nestedError === "string") {
      return nestedError;
    }
    if (
      nestedError &&
      typeof nestedError === "object" &&
      "message" in nestedError &&
      typeof (nestedError as { message?: unknown }).message === "string"
    ) {
      return (nestedError as { message: string }).message;
    }
  }

  if (typeof payload.message === "string") {
    return payload.message;
  }

  return fallback;
}

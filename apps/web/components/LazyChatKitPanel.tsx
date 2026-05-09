"use client";

import dynamic from "next/dynamic";
import type { FactAction } from "./ChatKitPanel";

export type { FactAction };

export const LazyChatKitPanel = dynamic(
  () => import("./ChatKitPanel").then((module) => module.ChatKitPanel),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-white text-sm text-slate-500 dark:bg-slate-900 dark:text-slate-300">
        법률 AI 에이전트를 준비하고 있습니다...
      </div>
    ),
  }
);

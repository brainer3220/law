"use client";

import { FormEvent } from "react";
import { useChat } from "@ai-sdk/react";
import { Send } from "lucide-react";
import { ToolTimeline } from "@/components/tool-timeline";
import type { ToolAwareMessage } from "@/lib/tool-messages";

export default function ChatPage() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, stop, reload } = useChat({
    api: "/api/chat",
    experimental_throttle: 50,
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    handleSubmit(event);
  };

  return (
    <div className="grid gap-6 p-6 lg:grid-cols-[minmax(0,3fr)_minmax(280px,1fr)]">
      <section className="space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">법률 상담 도우미</h1>
            <p className="text-sm text-slate-500">
              LangGraph 기반 백엔드와 연동하여 툴 호출을 실시간으로 확인하세요.
            </p>
          </div>
          <div className="flex gap-2 text-sm text-slate-400">
            {isLoading ? (
              <button
                className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100"
                onClick={() => stop()}
                type="button"
              >
                중단
              </button>
            ) : (
              <button
                className="rounded-md border border-slate-300 px-3 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100"
                onClick={() => reload()}
                type="button"
              >
                재실행
              </button>
            )}
          </div>
        </header>

        <div className="space-y-4">
          {messages.map((message) => (
            <article
              key={message.id}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  {message.role === "user" ? "🙋" : "🤖"}
                </div>
                <div className="space-y-2 text-sm leading-6 text-slate-700">
                  <p>{message.content}</p>
                  {message.parts?.filter((part) => part.type === "ui").map((part, idx) => (
                    <pre
                      key={idx}
                      className="overflow-x-auto rounded-md bg-slate-950/5 p-3 text-xs text-slate-600"
                    >
                      {JSON.stringify(part, null, 2)}
                    </pre>
                  ))}
                </div>
              </div>
            </article>
          ))}
        </div>

        <form onSubmit={onSubmit} className="sticky bottom-6 rounded-xl border border-slate-200 bg-white p-4 shadow-lg">
          <label className="mb-2 block text-xs font-medium uppercase tracking-wide text-slate-500">
            질문 입력
          </label>
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={handleInputChange}
              placeholder="근로시간 면제업무 관련 판례 알려줘"
              className="h-24 w-full resize-none rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-700 focus:border-slate-900 focus:outline-none"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="flex h-12 w-12 items-center justify-center rounded-lg bg-slate-900 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>
        </form>
      </section>

      <aside className="space-y-4">
        <ToolTimeline messages={messages as ToolAwareMessage[]} />
      </aside>
    </div>
  );
}

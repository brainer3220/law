"use client";

import { useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ToolAwareMessage, ToolMessagePart, ToolStatusPart } from "@/lib/tool-messages";

function statusToBadge(part: ToolMessagePart) {
  if (part.type === "tool-result") {
    return part.status === "error" ? "destructive" : "success";
  }

  if (part.type === "tool-status") {
    if (part.status === "error") return "destructive";
    if (part.status === "running") return "warning";
    if (part.status === "success") return "success";
  }

  return "default" as const;
}

const statusLabel: Record<ToolStatusPart["status"], string> = {
  started: "시작",
  running: "실행 중",
  success: "완료",
  error: "실패",
};

type ToolTimelineProps = {
  messages: ToolAwareMessage[];
};

export function ToolTimeline({ messages }: ToolTimelineProps) {
  const events = useMemo(
    () =>
      messages
        .flatMap((message) => message.parts ?? [])
        .filter((part) => part && typeof part === "object" && "type" in part)
        .filter((part): part is ToolMessagePart =>
          (part as { type: string }).type.startsWith("tool-")
        ),
    [messages]
  );

  if (events.length === 0) {
    return (
      <Card className="bg-slate-100/80">
        <CardHeader>
          <CardTitle>툴 활동</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500">
          아직 호출된 도구가 없습니다. 질문을 입력하면 사용 내역이 여기에 표시됩니다.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>툴 활동</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {events.map((part) => {
          const key = `${part.callId}-${part.type}`;
          const badgeVariant = statusToBadge(part);

          return (
            <div key={key} className="rounded-lg border border-slate-200 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {part.toolName}
                    {"stepId" in part && part.stepId ? (
                      <span className="ml-1 text-xs text-slate-400">#{part.stepId}</span>
                    ) : null}
                  </p>
                  <p className="text-xs text-slate-500">{part.type.replace("tool-", "")}</p>
                </div>
                <Badge variant={badgeVariant}>
                  {part.type === "tool-status" ? statusLabel[part.status] : "결과"}
                </Badge>
              </div>
              {"args" in part && part.args ? (
                <pre className="mt-3 overflow-x-auto rounded-md bg-slate-950/5 p-2 text-xs text-slate-700">
                  {JSON.stringify(part.args, null, 2)}
                </pre>
              ) : null}
              {"result" in part && part.result ? (
                <pre className="mt-3 overflow-x-auto rounded-md bg-emerald-50 p-2 text-xs text-emerald-800">
                  {JSON.stringify(part.result, null, 2)}
                </pre>
              ) : null}
              {"message" in part && part.message ? (
                <p className="mt-2 text-xs text-slate-500">{part.message}</p>
              ) : null}
              {"elapsedMs" in part && part.elapsedMs !== undefined ? (
                <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">
                  {part.elapsedMs}ms
                </p>
              ) : null}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

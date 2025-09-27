"use client";
import {
  AlertTriangle,
  ListTree,
  Repeat,
  Search,
  Workflow,
  Wrench,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { LawToolUsage } from "@/lib/types";

const formatPayload = (payload: Record<string, unknown> | undefined) => {
  if (!payload) {
    return undefined;
  }
  try {
    return JSON.stringify(payload, null, 2);
  } catch (error) {
    return undefined;
  }
};

const formatToolCallArguments = (value: string | undefined) => {
  if (!value) {
    return undefined;
  }
  try {
    const parsed = JSON.parse(value);
    return JSON.stringify(parsed, null, 2);
  } catch (error) {
    return value;
  }
};

export function LawToolUsageCard({ usage }: { usage: LawToolUsage }) {
  const hasContent =
    (usage.actions && usage.actions.length > 0) ||
    (usage.queries && usage.queries.length > 0) ||
    (usage.toolCalls && usage.toolCalls.length > 0) ||
    usage.iterations !== undefined ||
    !!usage.error;

  if (!hasContent) {
    return null;
  }

  return (
    <div className="space-y-4 rounded-lg border border-border/70 bg-muted/40 p-4 text-sm text-muted-foreground">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-foreground">
        <Wrench className="h-4 w-4" />
        <span>도구 사용 기록</span>
      </div>

      {usage.iterations !== undefined ? (
        <div className="flex items-center gap-2 text-foreground">
          <Repeat className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm">반복 횟수</span>
          <span className="font-semibold">{usage.iterations}</span>
        </div>
      ) : null}

      {usage.queries && usage.queries.length > 0 ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-foreground/80">
            <Search className="h-4 w-4" />
            <span>검색 질의</span>
          </div>
          <div className="flex flex-wrap gap-1">
            {usage.queries.map((query) => (
              <Badge key={query} variant="secondary">
                {query}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      {usage.actions && usage.actions.length > 0 ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-foreground/80">
            <ListTree className="h-4 w-4" />
            <span>실행된 도구</span>
          </div>
          <div className="space-y-2">
            {usage.actions.map((action, index) => {
              const payloadText = formatPayload(action.payload);
              return (
                <div
                  key={`${action.tool}-${index}`}
                  className="rounded-md border border-border/60 bg-background/70 p-3"
                >
                  <div className="text-sm font-medium text-foreground">
                    {action.tool}
                  </div>
                  {payloadText ? (
                    <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-muted/60 p-2 text-xs leading-relaxed text-foreground">
                      {payloadText}
                    </pre>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {usage.toolCalls && usage.toolCalls.length > 0 ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-foreground/80">
            <Workflow className="h-4 w-4" />
            <span>모델 도구 호출</span>
          </div>
          <div className="space-y-2">
            {usage.toolCalls.map((call, index) => {
              const argumentText = formatToolCallArguments(call.arguments);
              return (
                <div
                  key={`${call.id ?? call.name ?? index}`}
                  className="rounded-md border border-border/60 bg-background/70 p-3"
                >
                  <div className="flex flex-wrap items-center gap-2 text-sm text-foreground">
                    {call.name ? (
                      <span className="font-medium">{call.name}</span>
                    ) : null}
                    {call.id ? (
                      <span className="text-xs text-muted-foreground">#{call.id}</span>
                    ) : null}
                  </div>
                  {argumentText ? (
                    <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-muted/60 p-2 text-xs leading-relaxed text-foreground">
                      {argumentText}
                    </pre>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {usage.error ? (
        <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4" />
          <span className="text-sm">{usage.error}</span>
        </div>
      ) : null}
    </div>
  );
}

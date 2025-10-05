"use client";

import { useCompletion } from "@ai-sdk/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

const DEFAULT_PROMPT =
  "Please schedule a call with Sonny and Robby for tomorrow at 10am ET for me!";

export function McpDemo() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const { completion, complete, isLoading, error } = useCompletion({
    api: "/api/completion",
  });

  const errorMessage =
    typeof error === "string" ? error : error?.message ?? undefined;

  const handleSubmit = async () => {
    await complete(prompt);
  };

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Model Context Protocol demo</CardTitle>
          <CardDescription>
            Trigger the dedicated completion endpoint that merges MCP tools from
            stdio, Streamable HTTP, and SSE transports.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Textarea
            aria-label="MCP prompt"
            disabled={isLoading}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Enter a prompt to send to the MCP-enabled completion endpoint"
            value={prompt}
          />
          <div className="flex flex-row gap-2">
            <Button
              disabled={isLoading || !prompt.trim()}
              onClick={handleSubmit}
              type="button"
            >
              {isLoading ? "Running..." : "Run completion"}
            </Button>
            <Button
              disabled={isLoading}
              onClick={() => setPrompt(DEFAULT_PROMPT)}
              type="button"
              variant="outline"
            >
              Reset prompt
            </Button>
          </div>
          {errorMessage && (
            <p className="text-sm text-destructive">{errorMessage}</p>
          )}
          {completion && (
            <div className="rounded-md border bg-muted/30 p-4 text-sm whitespace-pre-wrap">
              {completion}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

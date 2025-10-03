"use client";

import { CodeBlock } from "@/components/elements/code-block";
import { Badge } from "@/components/ui/badge";
import type {
  LawInterpretationDetailResult,
  LawInterpretationSearchResult,
  LawKeywordSearchResult,
  LawMcpHit,
  LawStatuteDetailResult,
  LawStatuteSearchResult,
} from "@/lib/ai/tools/law";

function formatScore(score: number | null | undefined) {
  if (score === null || score === undefined) {
    return null;
  }

  return score.toFixed(3);
}

function MetadataItem({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  if (value === undefined || value === null || value === "") {
    return null;
  }

  return (
    <div className="flex flex-col">
      <span className="font-medium text-foreground text-[11px] uppercase tracking-wide">
        {label}
      </span>
      <span className="text-muted-foreground text-xs break-words">{value}</span>
    </div>
  );
}

function LawHits({ hits }: { hits: LawMcpHit[] }) {
  if (!hits.length) {
    return (
      <p className="rounded-md bg-muted/40 p-3 text-sm text-muted-foreground">
        No matching legal snippets were returned for the provided arguments.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {hits.map((hit, index) => {
        const score = formatScore(hit.score);
        return (
          <div
            key={`${hit.doc_id ?? hit.path ?? "hit"}-${index}`}
            className="space-y-3 rounded-md border bg-background p-3 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-semibold text-sm leading-5">
                  {hit.title || `Result ${index + 1}`}
                </p>
                {hit.source && (
                  <span className="text-xs text-muted-foreground">
                    {hit.source}
                  </span>
                )}
              </div>
              {score && <Badge variant="outline">score {score}</Badge>}
            </div>
            {hit.snippet && (
              <p className="whitespace-pre-wrap text-sm leading-6 text-muted-foreground">
                {hit.snippet}
              </p>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <MetadataItem label="Doc ID" value={hit.doc_id} />
              <MetadataItem label="Path" value={hit.path} />
              <MetadataItem label="Line" value={hit.line_no} />
              <MetadataItem label="Page" value={hit.page_index} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StructuredSection({
  title,
  data,
}: {
  title: string;
  data?: Record<string, unknown> | null;
}) {
  if (!data || Object.keys(data).length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <h5 className="font-semibold text-xs uppercase tracking-wide text-muted-foreground">
        {title}
      </h5>
      <CodeBlock code={JSON.stringify(data, null, 2)} language="json" />
    </div>
  );
}

export function LawKeywordSearchOutput({
  result,
}: {
  result: LawKeywordSearchResult;
}) {
  return (
    <div className="space-y-4">
      <LawHits hits={result.hits} />
    </div>
  );
}

export function LawStatuteSearchOutput({
  result,
}: {
  result: LawStatuteSearchResult;
}) {
  return (
    <div className="space-y-4">
      <LawHits hits={result.hits} />
      <StructuredSection title="law.go.kr response" data={result.response ?? null} />
    </div>
  );
}

export function LawStatuteDetailOutput({
  result,
}: {
  result: LawStatuteDetailResult;
}) {
  return (
    <div className="space-y-4">
      <LawHits hits={result.hits} />
      <StructuredSection title="Statute detail" data={result.detail ?? null} />
    </div>
  );
}

export function LawInterpretationSearchOutput({
  result,
}: {
  result: LawInterpretationSearchResult;
}) {
  return (
    <div className="space-y-4">
      <LawHits hits={result.hits} />
      <StructuredSection title="Interpretation response" data={result.response ?? null} />
    </div>
  );
}

export function LawInterpretationDetailOutput({
  result,
}: {
  result: LawInterpretationDetailResult;
}) {
  return (
    <div className="space-y-4">
      <LawHits hits={result.hits} />
      <StructuredSection title="Interpretation detail" data={result.detail ?? null} />
    </div>
  );
}

export function renderLawOutput(
  result:
    | LawKeywordSearchResult
    | LawStatuteSearchResult
    | LawStatuteDetailResult
    | LawInterpretationSearchResult
    | LawInterpretationDetailResult,
  type: "keyword" | "statute-search" | "statute-detail" | "interpretation-search" | "interpretation-detail"
) {
  switch (type) {
    case "keyword":
      return <LawKeywordSearchOutput result={result} />;
    case "statute-search":
      return <LawStatuteSearchOutput result={result} />;
    case "statute-detail":
      return <LawStatuteDetailOutput result={result} />;
    case "interpretation-search":
      return <LawInterpretationSearchOutput result={result} />;
    case "interpretation-detail":
      return <LawInterpretationDetailOutput result={result} />;
    default:
      return null;
  }
}

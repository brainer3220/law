/**
 * EvidenceCard - 근거 카드 컴포넌트
 * 
 * 법령/판례/문서 근거를 표시하는 카드.
 * 출처 유형, 제목/번호, 스니펫, pin-cite, "원문 열기" 버튼 포함.
 */

"use client";

import { useState } from "react";
import { type EvidenceSource } from "@/lib/types";
import { formatLegalReference, truncate, cn } from "@/lib/utils";

export interface EvidenceCardProps {
  evidence: EvidenceSource;
  onOpenSource?: (evidence: EvidenceSource) => void;
  compact?: boolean;
  className?: string;
}

const EVIDENCE_TYPE_LABELS = {
  statute: "법령",
  case: "판례",
  doc: "문서",
};

const EVIDENCE_TYPE_COLORS = {
  statute: "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950",
  case: "border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-950",
  doc: "border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900",
};

export function EvidenceCard({
  evidence,
  onOpenSource,
  compact = false,
  className,
}: EvidenceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const typeLabel = EVIDENCE_TYPE_LABELS[evidence.type];
  const colorClass = EVIDENCE_TYPE_COLORS[evidence.type];
  const reference = formatLegalReference({
    type: evidence.type,
    number: evidence.number,
    title: evidence.title,
  });

  const snippet = evidence.snippet;
  const shouldTruncate = compact && snippet.length > 150;
  const displaySnippet = shouldTruncate && !isExpanded 
    ? truncate(snippet, 150) 
    : snippet;

  const handleOpenSource = () => {
    if (onOpenSource) {
      onOpenSource(evidence);
    } else if (evidence.url) {
      window.open(evidence.url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <article
      className={cn(
        "rounded-lg border-l-4 p-4 shadow-sm transition-all hover:shadow-md",
        colorClass,
        className
      )}
      aria-labelledby={`evidence-${evidence.id}-title`}
    >
      {/* Header */}
      <header className="mb-2 flex items-start justify-between">
        <div className="flex-1">
          <span
            className="mb-1 inline-block rounded bg-white px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-gray-700 dark:bg-slate-800 dark:text-gray-300"
            aria-label={`출처 유형: ${typeLabel}`}
          >
            {typeLabel}
          </span>
          <h3
            id={`evidence-${evidence.id}-title`}
            className="text-sm font-bold text-gray-900 dark:text-gray-100"
          >
            {reference}
          </h3>
          {evidence.date && (
            <time
              className="mt-1 block text-xs text-gray-500 dark:text-gray-400"
              dateTime={evidence.date}
            >
              {evidence.date}
            </time>
          )}
        </div>
        {evidence.confidence !== undefined && (
          <div
            className="ml-2 text-xs font-medium text-gray-600 dark:text-gray-400"
            aria-label={`신뢰도: ${Math.round(evidence.confidence * 100)}%`}
          >
            {Math.round(evidence.confidence * 100)}%
          </div>
        )}
      </header>

      {/* Pin Cite */}
      {evidence.pinCite && (
        <div className="mb-2 inline-flex items-center gap-1 rounded bg-white px-2 py-1 text-xs font-mono text-gray-700 dark:bg-slate-800 dark:text-gray-300">
          <span className="text-gray-500 dark:text-gray-400">📍</span>
          {evidence.pinCite}
        </div>
      )}

      {/* Snippet */}
      <blockquote className="mb-3 border-l-2 border-gray-300 pl-3 text-sm italic text-gray-700 dark:border-gray-600 dark:text-gray-300">
        {displaySnippet}
      </blockquote>

      {/* Footer */}
      <footer className="flex items-center justify-between">
        {shouldTruncate && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
            aria-expanded={isExpanded}
          >
            {isExpanded ? "접기" : "더 보기"}
          </button>
        )}
        {(evidence.url || onOpenSource) && (
          <button
            onClick={handleOpenSource}
            className="ml-auto text-xs font-semibold text-blue-600 hover:underline dark:text-blue-400"
            aria-label={`${reference} 원문 열기`}
          >
            원문 열기 →
          </button>
        )}
      </footer>
    </article>
  );
}

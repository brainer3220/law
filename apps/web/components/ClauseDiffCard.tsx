/**
 * ClauseDiffCard - 조항 비교 카드 컴포넌트
 * 
 * 계약서 조항의 before/after Diff를 표시하고,
 * 위험 태그, 인용 각주를 포함하는 카드.
 */

"use client";

import { useState } from "react";
import { type ClauseDiff } from "@/lib/types";
import { RiskBadge } from "./RiskBadge";
import { EvidenceCard } from "./EvidenceCard";
import { cn } from "@/lib/utils";

interface ClauseDiffCardProps {
  diff: ClauseDiff;
  onAccept?: (diffId: string) => void;
  onReject?: (diffId: string) => void;
  onRevise?: (diffId: string) => void;
  className?: string;
}

export function ClauseDiffCard({
  diff,
  onAccept,
  onReject,
  onRevise,
  className,
}: ClauseDiffCardProps) {
  const [showEvidence, setShowEvidence] = useState(false);
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");

  const hasCitations = diff.citations.length > 0;

  return (
    <article
      className={cn(
        "rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-slate-900",
        className
      )}
      aria-labelledby={`diff-${diff.id}-title`}
    >
      {/* Header */}
      <header className="mb-4 flex items-start justify-between">
        <div className="flex-1">
          <h3
            id={`diff-${diff.id}-title`}
            className="mb-2 text-base font-bold text-gray-900 dark:text-gray-100"
          >
            조항 변경 제안
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge level={diff.riskLevel} />
            {diff.riskTags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
        {/* View Mode Toggle */}
        <div className="ml-4 flex rounded-lg border border-gray-300 dark:border-gray-600">
          <button
            onClick={() => setViewMode("unified")}
            className={cn(
              "rounded-l-lg px-3 py-1 text-xs font-medium transition-colors",
              viewMode === "unified"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700"
            )}
            aria-pressed={viewMode === "unified"}
          >
            통합
          </button>
          <button
            onClick={() => setViewMode("split")}
            className={cn(
              "rounded-r-lg border-l border-gray-300 px-3 py-1 text-xs font-medium transition-colors dark:border-gray-600",
              viewMode === "split"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 hover:bg-gray-50 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700"
            )}
            aria-pressed={viewMode === "split"}
          >
            분할
          </button>
        </div>
      </header>

      {/* Diff Content */}
      {viewMode === "unified" ? (
        <div className="mb-4 space-y-3">
          {/* Before */}
          <div className="rounded-md bg-red-50 p-3 dark:bg-red-950/30">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-700 dark:text-red-400">
              이전 (Before)
            </div>
            <p className="text-sm leading-relaxed text-gray-800 line-through dark:text-gray-300">
              {diff.before}
            </p>
          </div>
          {/* After */}
          <div className="rounded-md bg-green-50 p-3 dark:bg-green-950/30">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
              이후 (After)
            </div>
            <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-300">
              {diff.after}
            </p>
          </div>
        </div>
      ) : (
        <div className="mb-4 grid grid-cols-2 gap-4">
          {/* Before */}
          <div className="rounded-md bg-red-50 p-3 dark:bg-red-950/30">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-red-700 dark:text-red-400">
              이전 (Before)
            </div>
            <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-300">
              {diff.before}
            </p>
          </div>
          {/* After */}
          <div className="rounded-md bg-green-50 p-3 dark:bg-green-950/30">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
              이후 (After)
            </div>
            <p className="text-sm leading-relaxed text-gray-800 dark:text-gray-300">
              {diff.after}
            </p>
          </div>
        </div>
      )}

      {/* Comments */}
      {diff.comments && (
        <div className="mb-4 rounded-md border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-950/30">
          <div className="mb-1 text-xs font-semibold text-blue-700 dark:text-blue-400">
            💬 검토 의견
          </div>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {diff.comments}
          </p>
        </div>
      )}

      {/* Citations Toggle */}
      {hasCitations && (
        <button
          onClick={() => setShowEvidence(!showEvidence)}
          className="mb-3 flex w-full items-center justify-between rounded-md bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          aria-expanded={showEvidence}
        >
          <span>📚 인용 근거 ({diff.citations.length})</span>
          <span aria-hidden="true">{showEvidence ? "▼" : "▶"}</span>
        </button>
      )}

      {/* Citations List */}
      {showEvidence && hasCitations && (
        <div className="mb-4 space-y-3">
          {diff.citations.map((evidence) => (
            <EvidenceCard
              key={evidence.id}
              evidence={evidence}
              compact
            />
          ))}
        </div>
      )}

      {/* Actions */}
      <footer className="flex items-center justify-end gap-2 border-t border-gray-200 pt-4 dark:border-gray-700">
        {onReject && (
          <button
            onClick={() => onReject(diff.id)}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            거부
          </button>
        )}
        {onRevise && (
          <button
            onClick={() => onRevise(diff.id)}
            className="rounded-md border border-blue-300 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900"
          >
            수정 요청
          </button>
        )}
        {onAccept && (
          <button
            onClick={() => onAccept(diff.id)}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600"
          >
            승인
          </button>
        )}
      </footer>
    </article>
  );
}

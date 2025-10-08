/**
 * ClaimEvidenceMatrix - 주장 × 근거 매트릭스 컴포넌트
 * 
 * 문서의 주장(Claims)과 근거(Evidence)의 관계를 매트릭스 형태로 시각화.
 * 각 셀은 주장과 근거 간의 관련도와 정합성을 아이콘으로 표시.
 */

"use client";

import { useState } from "react";
import { type Claim, type EvidenceSource, type ClaimEvidenceCell } from "@/lib/types";
import { cn, getCiteStatusColorClass } from "@/lib/utils";

export interface ClaimEvidenceMatrixProps {
  claims: Claim[];
  evidence: EvidenceSource[];
  cells: ClaimEvidenceCell[];
  onCellClick?: (claimId: string, evidenceId: string) => void;
  className?: string;
}

export function ClaimEvidenceMatrix({
  claims,
  evidence,
  cells,
  onCellClick,
  className,
}: ClaimEvidenceMatrixProps) {
  const [selectedCell, setSelectedCell] = useState<{
    claimId: string;
    evidenceId: string;
  } | null>(null);

  const getCellData = (claimId: string, evidenceId: string) => {
    return cells.find(
      (c) => c.claimId === claimId && c.evidenceId === evidenceId
    );
  };

  const handleCellClick = (claimId: string, evidenceId: string) => {
    setSelectedCell({ claimId, evidenceId });
    onCellClick?.(claimId, evidenceId);
  };

  const renderCellIcon = (cell: ClaimEvidenceCell | undefined) => {
    if (!cell) {
      return <span className="text-gray-300 dark:text-gray-600">—</span>;
    }

    const { relevance, isSupporting } = cell;
    
    if (!isSupporting) {
      return (
        <span
          className="text-red-500 dark:text-red-400"
          title="뒷받침하지 않음"
          aria-label="뒷받침하지 않음"
        >
          ✗
        </span>
      );
    }

    if (relevance >= 0.8) {
      return (
        <span
          className="text-green-600 dark:text-green-400"
          title={`관련도 높음 (${Math.round(relevance * 100)}%)`}
          aria-label={`관련도 높음 (${Math.round(relevance * 100)}%)`}
        >
          ●●●
        </span>
      );
    }

    if (relevance >= 0.5) {
      return (
        <span
          className="text-amber-500 dark:text-amber-400"
          title={`관련도 중간 (${Math.round(relevance * 100)}%)`}
          aria-label={`관련도 중간 (${Math.round(relevance * 100)}%)`}
        >
          ●●○
        </span>
      );
    }

    return (
      <span
        className="text-gray-500 dark:text-gray-400"
        title={`관련도 낮음 (${Math.round(relevance * 100)}%)`}
        aria-label={`관련도 낮음 (${Math.round(relevance * 100)}%)`}
      >
        ●○○
      </span>
    );
  };

  if (claims.length === 0 || evidence.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-slate-900">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          매트릭스를 표시할 주장 또는 근거가 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-slate-900",
        className
      )}
      role="table"
      aria-label="주장과 근거의 관계 매트릭스"
    >
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-slate-800">
            <th
              className="sticky left-0 z-10 bg-gray-50 px-4 py-3 text-left font-semibold text-gray-700 dark:bg-slate-800 dark:text-gray-300"
              scope="col"
            >
              주장 (Claims)
            </th>
            {evidence.map((ev) => (
              <th
                key={ev.id}
                className="min-w-[120px] px-3 py-3 text-center font-semibold text-gray-700 dark:text-gray-300"
                scope="col"
                title={ev.title}
              >
                <div className="flex flex-col items-center gap-1">
                  <span className="text-xs uppercase text-gray-500 dark:text-gray-400">
                    {ev.type === "statute" && "📜"}
                    {ev.type === "case" && "⚖️"}
                    {ev.type === "doc" && "📄"}
                  </span>
                  <span className="line-clamp-2 text-xs">
                    {ev.title.length > 20
                      ? `${ev.title.slice(0, 20)}...`
                      : ev.title}
                  </span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {claims.map((claim, claimIdx) => (
            <tr
              key={claim.id}
              className={cn(
                "border-b border-gray-100 dark:border-gray-800",
                claimIdx % 2 === 0
                  ? "bg-white dark:bg-slate-900"
                  : "bg-gray-50/50 dark:bg-slate-800/50"
              )}
            >
              <th
                className="sticky left-0 z-10 px-4 py-3 text-left font-medium text-gray-900 dark:text-gray-100"
                scope="row"
                style={{
                  backgroundColor:
                    claimIdx % 2 === 0
                      ? "inherit"
                      : "rgb(249 250 251 / 0.5)",
                }}
              >
                <div className="flex items-start gap-2">
                  <span
                    className={cn(
                      "mt-0.5 flex-shrink-0 text-xs",
                      getCiteStatusColorClass(claim.status)
                    )}
                  >
                    {claim.status === "verified" && "✓"}
                    {claim.status === "unverified" && "?"}
                    {claim.status === "error" && "✗"}
                  </span>
                  <span
                    className="line-clamp-2 text-xs"
                    title={claim.text}
                  >
                    {claim.text.length > 60
                      ? `${claim.text.slice(0, 60)}...`
                      : claim.text}
                  </span>
                </div>
              </th>
              {evidence.map((ev) => {
                const cellData = getCellData(claim.id, ev.id);
                const isSelected =
                  selectedCell?.claimId === claim.id &&
                  selectedCell?.evidenceId === ev.id;

                return (
                  <td
                    key={ev.id}
                    className={cn(
                      "cursor-pointer border-l border-gray-100 px-3 py-3 text-center transition-colors hover:bg-blue-50 dark:border-gray-800 dark:hover:bg-blue-950/30",
                      isSelected &&
                        "bg-blue-100 dark:bg-blue-900/50"
                    )}
                    onClick={() => handleCellClick(claim.id, ev.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        handleCellClick(claim.id, ev.id);
                      }
                    }}
                    aria-label={`주장 ${claimIdx + 1}과 근거 ${ev.title}의 관계`}
                  >
                    {renderCellIcon(cellData)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <footer className="border-t border-gray-200 bg-gray-50 px-4 py-3 dark:border-gray-700 dark:bg-slate-800">
        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
          <span className="font-semibold">범례:</span>
          <span className="flex items-center gap-1">
            <span className="text-green-600 dark:text-green-400">●●●</span>
            높은 관련도
          </span>
          <span className="flex items-center gap-1">
            <span className="text-amber-500 dark:text-amber-400">●●○</span>
            중간 관련도
          </span>
          <span className="flex items-center gap-1">
            <span className="text-gray-500 dark:text-gray-400">●○○</span>
            낮은 관련도
          </span>
          <span className="flex items-center gap-1">
            <span className="text-red-500 dark:text-red-400">✗</span>
            뒷받침하지 않음
          </span>
          <span className="flex items-center gap-1">
            <span className="text-gray-300 dark:text-gray-600">—</span>
            관계 없음
          </span>
        </div>
      </footer>
    </div>
  );
}

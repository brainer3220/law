/**
 * ProvenanceFooter - Provenance 정보 표시 컴포넌트
 * 
 * 모델 버전, 프롬프트 버전, 인덱스 버전, 정책 버전 등
 * 출처 정보를 푸터에 표시하여 투명성 확보.
 */

"use client";

import { useState } from "react";
import { type Provenance } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

export interface ProvenanceFooterProps {
  provenance: Provenance;
  auditId?: string;
  className?: string;
}

export function ProvenanceFooter({
  provenance,
  auditId,
  className,
}: ProvenanceFooterProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <footer
      className={cn(
        "border-t border-gray-200 bg-gray-50 px-4 py-3 text-xs text-gray-600 dark:border-gray-700 dark:bg-slate-800 dark:text-gray-400",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 font-medium hover:text-gray-900 dark:hover:text-gray-200"
          aria-expanded={isExpanded}
          aria-label="출처 정보 보기"
        >
          <span>📋 Provenance</span>
          <span aria-hidden="true">{isExpanded ? "▼" : "▶"}</span>
        </button>
        <time
          className="text-gray-500 dark:text-gray-500"
          dateTime={provenance.timestamp}
        >
          생성: {formatDate(provenance.timestamp)}
        </time>
      </div>

      {isExpanded && (
        <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 rounded-md border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-slate-900">
          <div>
            <span className="font-semibold">모델 버전:</span>{" "}
            <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs dark:bg-gray-800">
              {provenance.modelVersion}
            </code>
          </div>
          <div>
            <span className="font-semibold">프롬프트 버전:</span>{" "}
            <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs dark:bg-gray-800">
              {provenance.promptVersion}
            </code>
          </div>
          <div>
            <span className="font-semibold">인덱스 버전:</span>{" "}
            <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs dark:bg-gray-800">
              {provenance.indexVersion}
            </code>
          </div>
          <div>
            <span className="font-semibold">정책 버전:</span>{" "}
            <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs dark:bg-gray-800">
              {provenance.policyVersion}
            </code>
          </div>
          {provenance.corpusHash && (
            <div className="col-span-2">
              <span className="font-semibold">코퍼스 해시:</span>{" "}
              <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs dark:bg-gray-800">
                {provenance.corpusHash.slice(0, 16)}...
              </code>
            </div>
          )}
          {auditId && (
            <div className="col-span-2">
              <span className="font-semibold">감사 ID:</span>{" "}
              <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs dark:bg-gray-800">
                {auditId}
              </code>
            </div>
          )}
        </div>
      )}
    </footer>
  );
}

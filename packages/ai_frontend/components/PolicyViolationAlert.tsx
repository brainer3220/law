/**
 * PolicyViolationAlert - 정책 위반 알림 컴포넌트
 * 
 * UPL, 프라이버시, 범위 초과, Hallucination 등
 * 정책 위반 사항을 경고 형태로 표시.
 */

"use client";

import { type PolicyViolation } from "@/lib/types";
import { RiskBadge } from "./RiskBadge";
import { cn } from "@/lib/utils";

export interface PolicyViolationAlertProps {
  violations: PolicyViolation[];
  onResolve?: (violationId: string) => void;
  onViewGuide?: (violation: PolicyViolation) => void;
  className?: string;
}

const VIOLATION_TYPE_LABELS: Record<PolicyViolation["type"], string> = {
  upl: "무면허 법률 서비스",
  privacy: "개인정보 침해",
  scope: "Matter 범위 초과",
  hallucination: "근거 없는 주장",
};

const VIOLATION_TYPE_ICONS: Record<PolicyViolation["type"], string> = {
  upl: "⚠️",
  privacy: "🔒",
  scope: "🚧",
  hallucination: "🚨",
};

export function PolicyViolationAlert({
  violations,
  onResolve,
  onViewGuide,
  className,
}: PolicyViolationAlertProps) {
  if (violations.length === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        "rounded-lg border border-red-300 bg-red-50 p-4 shadow-sm dark:border-red-800 dark:bg-red-950/30",
        className
      )}
      role="alert"
      aria-live="assertive"
    >
      <div className="mb-3 flex items-center gap-2">
        <span className="text-lg" aria-hidden="true">
          🚨
        </span>
        <h3 className="text-sm font-bold text-red-900 dark:text-red-300">
          정책 위반 감지 ({violations.length}건)
        </h3>
      </div>

      <ul className="space-y-3">
        {violations.map((violation) => (
          <li
            key={violation.id}
            className="rounded-md border border-red-200 bg-white p-3 dark:border-red-900 dark:bg-slate-900"
          >
            <div className="mb-2 flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span aria-hidden="true">
                  {VIOLATION_TYPE_ICONS[violation.type]}
                </span>
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                  {VIOLATION_TYPE_LABELS[violation.type]}
                </span>
                <RiskBadge level={violation.severity} showIcon={false} />
              </div>
            </div>

            <p className="mb-2 text-sm text-gray-700 dark:text-gray-300">
              {violation.message}
            </p>

            {violation.location && (
              <div className="mb-2 text-xs text-gray-500 dark:text-gray-400">
                위치: 문단 {violation.location.paragraph}, 문자{" "}
                {violation.location.start}~{violation.location.end}
              </div>
            )}

            {violation.suggestion && (
              <div className="mb-2 rounded bg-blue-50 p-2 text-sm text-blue-900 dark:bg-blue-950/50 dark:text-blue-300">
                <strong className="font-semibold">💡 제안:</strong>{" "}
                {violation.suggestion}
              </div>
            )}

            <div className="flex items-center gap-2">
              {violation.guideUrl && onViewGuide && (
                <button
                  onClick={() => onViewGuide(violation)}
                  className="text-xs font-medium text-blue-600 hover:underline dark:text-blue-400"
                >
                  가이드 보기
                </button>
              )}
              {onResolve && (
                <button
                  onClick={() => onResolve(violation.id)}
                  className="ml-auto rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700 dark:bg-green-700 dark:hover:bg-green-600"
                >
                  해결됨으로 표시
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

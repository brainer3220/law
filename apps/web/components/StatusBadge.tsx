/**
 * StatusBadge - 문서 상태 뱃지 컴포넌트
 * 
 * Draft → CiteCheck → PolicyCheck → Approved 등
 * 문서 처리 상태를 시각적으로 표시.
 */

import { cn } from "@/lib/utils";

type DocumentStatus = "draft" | "cite_check" | "policy_check" | "approved";

interface StatusBadgeProps {
  status: DocumentStatus;
  showIcon?: boolean;
  className?: string;
}

const STATUS_CONFIG: Record<
  DocumentStatus,
  { label: string; icon: string; colorClass: string }
> = {
  draft: {
    label: "초안",
    icon: "📝",
    colorClass: "text-gray-600 bg-gray-100 dark:text-gray-400 dark:bg-gray-800",
  },
  cite_check: {
    label: "인용 검증 중",
    icon: "🔍",
    colorClass: "text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-950",
  },
  policy_check: {
    label: "정책 검토 중",
    icon: "⚖️",
    colorClass: "text-amber-600 bg-amber-100 dark:text-amber-400 dark:bg-amber-950",
  },
  approved: {
    label: "승인됨",
    icon: "✅",
    colorClass: "text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-950",
  },
};

export function StatusBadge({
  status,
  showIcon = true,
  className,
}: StatusBadgeProps) {
  const config = STATUS_CONFIG[status];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
        config.colorClass,
        className
      )}
      role="status"
      aria-label={`문서 상태: ${config.label}`}
    >
      {showIcon && <span aria-hidden="true">{config.icon}</span>}
      <span>{config.label}</span>
    </span>
  );
}

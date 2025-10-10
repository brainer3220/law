/**
 * RiskBadge - 위험도 뱃지 컴포넌트
 * 
 * 위험도(High/Medium/Low)를 시각적으로 표시하는 뱃지.
 * 색맹 친화적 아이콘과 색상 사용.
 */

import { type RiskLevel } from "@/lib/types";
import { getRiskColorClass, cn } from "@/lib/utils";

export interface RiskBadgeProps {
  level: RiskLevel;
  label?: string;
  showIcon?: boolean;
  className?: string;
}

const RISK_LABELS: Record<RiskLevel, string> = {
  high: "높음",
  medium: "중간",
  low: "낮음",
};

const RISK_ICONS: Record<RiskLevel, string> = {
  high: "⚠",
  medium: "⚡",
  low: "✓",
};

export function RiskBadge({
  level,
  label,
  showIcon = true,
  className,
}: RiskBadgeProps) {
  const displayLabel = label ?? RISK_LABELS[level];
  const icon = RISK_ICONS[level];
  const colorClass = getRiskColorClass(level);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        colorClass,
        className
      )}
      role="status"
      aria-label={`위험도: ${displayLabel}`}
    >
      {showIcon && <span aria-hidden="true">{icon}</span>}
      <span>{displayLabel}</span>
    </span>
  );
}

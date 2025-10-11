/**
 * LoadingSpinner - 로딩 스피너 컴포넌트
 * 
 * 데이터 로딩, 비동기 작업 진행 중 표시.
 */

import "@material/web/progress/circular-progress.js";
import { cn } from "@/lib/utils";
import type { CSSProperties } from "react";

export interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

const SIZE_STYLES: Record<
  NonNullable<LoadingSpinnerProps["size"]>,
  CSSProperties
> = {
  sm: { width: "20px", height: "20px" },
  md: { width: "32px", height: "32px" },
  lg: { width: "44px", height: "44px" },
};

export function LoadingSpinner({
  size = "md",
  label = "로딩 중...",
  className,
}: LoadingSpinnerProps) {
  const sizeStyle = SIZE_STYLES[size];

  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-2", className)}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <md-circular-progress
        indeterminate
        style={sizeStyle}
        aria-hidden="true"
      />
      {label && (
        <span className="material-support-text">{label}</span>
      )}
    </div>
  );
}

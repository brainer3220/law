/**
 * CitationPopover - 인용 팝오버 컴포넌트
 * 
 * 문단의 특정 부분에 호버하거나 클릭하면 나타나는 팝오버로,
 * 해당 주장을 뒷받침하는 근거(법령/판례/문서)를 표시.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { type EvidenceSource, type CitationStatus } from "@/lib/types";
import { getCiteStatusColorClass, cn } from "@/lib/utils";
import { EvidenceCard } from "./EvidenceCard";

export interface CitationPopoverProps {
  text: string;
  evidence: EvidenceSource[];
  status: CitationStatus;
  onOpenSource?: (evidence: EvidenceSource) => void;
  className?: string;
}

const CITATION_STATUS_LABELS: Record<CitationStatus, string> = {
  unverified: "검증 전",
  verified: "검증됨",
  error: "오류",
};

export function CitationPopover({
  text,
  evidence,
  status,
  onOpenSource,
  className,
}: CitationPopoverProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState<"top" | "bottom">("bottom");
  const triggerRef = useRef<HTMLSpanElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // 팝오버 위치 계산 (화면 밖으로 나가지 않도록)
  useEffect(() => {
    if (!isOpen || !triggerRef.current || !popoverRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const popoverRect = popoverRef.current.getBoundingClientRect();
    const viewportHeight = window.innerHeight;

    // 하단에 공간이 부족하면 상단에 표시
    if (triggerRect.bottom + popoverRect.height + 10 > viewportHeight) {
      setPosition("top");
    } else {
      setPosition("bottom");
    }
  }, [isOpen]);

  // 외부 클릭 시 닫기
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const statusLabel = CITATION_STATUS_LABELS[status];
  const statusColorClass = getCiteStatusColorClass(status);

  return (
    <span className={cn("relative inline", className)}>
      {/* Trigger */}
      <span
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => {
          // 마우스가 popover로 이동할 수 있도록 약간의 딜레이
          setTimeout(() => {
            if (
              popoverRef.current &&
              !popoverRef.current.matches(":hover")
            ) {
              setIsOpen(false);
            }
          }, 200);
        }}
        className={cn(
          "cursor-pointer border-b-2 border-dotted font-medium transition-colors",
          statusColorClass,
          "hover:opacity-80"
        )}
        role="button"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        aria-label={`인용 근거 보기: ${statusLabel}`}
      >
        {text}
        <sup className="ml-0.5 text-xs">[{evidence.length}]</sup>
      </span>

      {/* Popover */}
      {isOpen && (
        <div
          ref={popoverRef}
          className={cn(
            "absolute z-50 w-96 rounded-lg border border-gray-300 bg-white shadow-xl dark:border-gray-600 dark:bg-slate-800",
            position === "top" ? "bottom-full mb-2" : "top-full mt-2",
            "left-1/2 -translate-x-1/2"
          )}
          role="dialog"
          aria-label="인용 근거 상세"
          onMouseLeave={() => setIsOpen(false)}
        >
          {/* Header */}
          <header className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                인용 근거
              </h4>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-semibold",
                  statusColorClass
                )}
              >
                {statusLabel}
              </span>
            </div>
          </header>

          {/* Evidence List */}
          <div className="max-h-96 overflow-y-auto p-4">
            {evidence.length === 0 ? (
              <p className="text-sm italic text-gray-500 dark:text-gray-400">
                인용 근거가 없습니다.
              </p>
            ) : (
              <div className="space-y-3">
                {evidence.map((ev) => (
                  <EvidenceCard
                    key={ev.id}
                    evidence={ev}
                    onOpenSource={onOpenSource}
                    compact
                  />
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <footer className="border-t border-gray-200 px-4 py-2 dark:border-gray-700">
            <button
              onClick={() => setIsOpen(false)}
              className="text-xs font-medium text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
            >
              닫기
            </button>
          </footer>
        </div>
      )}
    </span>
  );
}

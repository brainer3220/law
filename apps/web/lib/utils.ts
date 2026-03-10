/**
 * 공유 유틸리티 함수
 * 법률 LLM 에이전트 프론트엔드 공통 로직
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Tailwind CSS 클래스 병합 유틸리티
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 날짜 포맷팅 (한국어)
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(d);
}

/**
 * 법령/판례 번호 포맷팅
 */
export function formatLegalReference(ref: {
  type: "statute" | "case" | "doc";
  number?: string;
  title: string;
}): string {
  if (ref.type === "statute") {
    return ref.number ? `${ref.title} ${ref.number}` : ref.title;
  }
  if (ref.type === "case") {
    return ref.number ? `${ref.number} ${ref.title}` : ref.title;
  }
  return ref.title;
}

/**
 * 텍스트 절단 (말줄임)
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

/**
 * 위험도 레벨에 따른 색상 클래스
 */
export function getRiskColorClass(level: "high" | "medium" | "low"): string {
  switch (level) {
    case "high":
      return "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950";
    case "medium":
      return "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950";
    case "low":
      return "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950";
  }
}

/**
 * 인용 상태에 따른 색상 클래스
 */
export function getCiteStatusColorClass(
  status: "unverified" | "verified" | "error"
): string {
  switch (status) {
    case "unverified":
      return "text-gray-500 dark:text-gray-400";
    case "verified":
      return "text-blue-600 dark:text-blue-400";
    case "error":
      return "text-red-600 dark:text-red-400";
  }
}

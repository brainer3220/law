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
 * 텍스트 하이라이트 (검색어 강조)
 */
export function highlightText(
  text: string,
  query: string,
  className = "bg-yellow-200 dark:bg-yellow-800"
): string {
  if (!query.trim()) return text;
  
  const regex = new RegExp(`(${escapeRegex(query)})`, "gi");
  return text.replace(regex, `<mark class="${className}">$1</mark>`);
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 텍스트 절단 (말줄임)
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

/**
 * Pin cite 파싱 (예: "제10조 제2항" → { article: 10, paragraph: 2 })
 */
export function parsePinCite(cite: string): {
  article?: number;
  paragraph?: number;
  raw: string;
} {
  const articleMatch = cite.match(/제(\d+)조/);
  const paragraphMatch = cite.match(/제(\d+)항/);
  
  return {
    article: articleMatch ? parseInt(articleMatch[1], 10) : undefined,
    paragraph: paragraphMatch ? parseInt(paragraphMatch[1], 10) : undefined,
    raw: cite,
  };
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

/**
 * PII 마스킹 (주민등록번호, 전화번호 등)
 */
export function maskPII(text: string): string {
  // 주민등록번호: 123456-1234567 → 123456-*******
  let masked = text.replace(
    /(\d{6})-(\d{7})/g,
    (_, p1) => `${p1}-*******`
  );
  
  // 전화번호: 010-1234-5678 → 010-****-5678
  masked = masked.replace(
    /(\d{2,3})-(\d{3,4})-(\d{4})/g,
    (_, p1, __, p3) => `${p1}-****-${p3}`
  );
  
  return masked;
}

/**
 * 파일 크기 포맷팅
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Debounce 함수
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };
    
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * 깊은 객체 복사
 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * 배열을 청크로 분할
 */
export function chunkArray<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

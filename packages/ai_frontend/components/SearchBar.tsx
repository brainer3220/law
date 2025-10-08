/**
 * SearchBar - 검색 바 컴포넌트
 * 
 * 법령/판례/문서 검색을 위한 검색 바.
 * Debounce, 필터, 자동완성 기능 포함.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import { type SearchFilter } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface SearchBarProps {
  onSearch: (filter: SearchFilter) => void;
  placeholder?: string;
  showFilters?: boolean;
  className?: string;
}

export function SearchBar({
  onSearch,
  placeholder = "법령, 판례, 문서 검색...",
  showFilters = false,
  className,
}: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [filter, setFilter] = useState<Omit<SearchFilter, "query">>({});
  const inputRef = useRef<HTMLInputElement>(null);
  
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery.trim()) {
      onSearch({ query: debouncedQuery, ...filter });
    }
  }, [debouncedQuery, filter, onSearch]);

  const handleClear = () => {
    setQuery("");
    setFilter({});
    inputRef.current?.focus();
  };

  return (
    <div className={cn("relative", className)}>
      {/* Search Input */}
      <div className="relative flex items-center">
        <div className="pointer-events-none absolute left-3 text-gray-400">
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-20 text-sm text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-gray-600 dark:bg-slate-800 dark:text-gray-100 dark:placeholder-gray-400"
          aria-label="검색"
        />
        <div className="absolute right-2 flex items-center gap-1">
          {query && (
            <button
              onClick={handleClear}
              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
              aria-label="검색어 지우기"
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          )}
          {showFilters && (
            <button
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className={cn(
                "rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300",
                isFilterOpen && "bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400"
              )}
              aria-label="필터"
              aria-expanded={isFilterOpen}
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && isFilterOpen && (
        <div className="absolute top-full z-50 mt-2 w-full rounded-lg border border-gray-300 bg-white p-4 shadow-lg dark:border-gray-600 dark:bg-slate-800">
          <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-gray-100">
            필터
          </h4>
          <div className="space-y-3">
            {/* Domain Filter */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                법률 분야
              </label>
              <select
                value={filter.domain ?? ""}
                onChange={(e) =>
                  setFilter((prev) => ({
                    ...prev,
                    domain: (e.target.value as any) || undefined,
                  }))
                }
                className="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 dark:border-gray-600 dark:bg-slate-700 dark:text-gray-100"
              >
                <option value="">전체</option>
                <option value="civil">민사</option>
                <option value="criminal">형사</option>
                <option value="administrative">행정</option>
                <option value="ip">지적재산권</option>
              </select>
            </div>

            {/* Corpus Filter */}
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                출처 유형
              </label>
              <div className="space-y-1">
                {["statute", "case", "doc"].map((type) => (
                  <label
                    key={type}
                    className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
                  >
                    <input
                      type="checkbox"
                      checked={filter.corpus?.includes(type as any) ?? false}
                      onChange={(e) => {
                        const current = filter.corpus ?? [];
                        const updated = e.target.checked
                          ? [...current, type as any]
                          : current.filter((t) => t !== type);
                        setFilter((prev) => ({
                          ...prev,
                          corpus: updated.length > 0 ? updated : undefined,
                        }));
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    {type === "statute" && "법령"}
                    {type === "case" && "판례"}
                    {type === "doc" && "문서"}
                  </label>
                ))}
              </div>
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                  시작일
                </label>
                <input
                  type="date"
                  value={filter.dateFrom ?? ""}
                  onChange={(e) =>
                    setFilter((prev) => ({
                      ...prev,
                      dateFrom: e.target.value || undefined,
                    }))
                  }
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 dark:border-gray-600 dark:bg-slate-700 dark:text-gray-100"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                  종료일
                </label>
                <input
                  type="date"
                  value={filter.dateTo ?? ""}
                  onChange={(e) =>
                    setFilter((prev) => ({
                      ...prev,
                      dateTo: e.target.value || undefined,
                    }))
                  }
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm text-gray-900 dark:border-gray-600 dark:bg-slate-700 dark:text-gray-100"
                />
              </div>
            </div>

            {/* Reset Button */}
            <button
              onClick={() => {
                setFilter({});
                setIsFilterOpen(false);
              }}
              className="w-full rounded-md bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
            >
              필터 초기화
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

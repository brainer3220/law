/**
 * useDebounce Hook
 * 
 * 값의 변경을 지연시켜 빈번한 업데이트를 방지.
 * 검색 입력, API 호출 등에 유용.
 */

import { useEffect, useState } from "react";

export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

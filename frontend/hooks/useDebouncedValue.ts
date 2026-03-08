'use client';

import { useState, useEffect } from 'react';

/**
 * 값이 변경된 후 지정된 지연 시간이 지나야 업데이트되는 디바운스 훅.
 * 검색 입력, 필터 등에서 매 키스트로크마다 상태 업데이트를 방지.
 */
export function useDebouncedValue<T>(value: T, delayMs: number = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}

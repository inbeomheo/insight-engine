'use client';

import { useState, useCallback } from 'react';

interface UseListManagerReturn<T> {
  items: T[];
  add: (item: T) => void;
  remove: (index: number) => void;
  update: (index: number, item: T) => void;
  set: (items: T[]) => void;
  clear: () => void;
}

/**
 * 배열 상태의 add/remove/update 보일러플레이트를 제거하는 훅.
 * MemoryManager 등에서 반복되는 태그/리스트 관리 패턴 통합.
 */
export function useListManager<T>(initial: T[] = []): UseListManagerReturn<T> {
  const [items, setItems] = useState<T[]>(initial);

  const add = useCallback((item: T) => {
    setItems((prev) => [...prev, item]);
  }, []);

  const remove = useCallback((index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const update = useCallback((index: number, item: T) => {
    setItems((prev) => prev.map((v, i) => (i === index ? item : v)));
  }, []);

  const clear = useCallback(() => setItems([]), []);

  return { items, add, remove, update, set: setItems, clear };
}

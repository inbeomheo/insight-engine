'use client';

import { useState, useCallback } from 'react';
import { toast } from 'sonner';

interface UseApiCallReturn<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  execute: (fn: () => Promise<T>, errorMsg?: string) => Promise<T | null>;
  reset: () => void;
}

/**
 * API 호출의 loading/error/toast 보일러플레이트를 제거하는 훅.
 * try-catch + setState + toast 패턴을 1줄로 축소.
 */
export function useApiCall<T = unknown>(): UseApiCallReturn<T> {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = useCallback(async (fn: () => Promise<T>, errorMsg?: string): Promise<T | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fn();
      setData(result);
      return result;
    } catch (err) {
      const msg = errorMsg || (err instanceof Error ? err.message : '요청에 실패했습니다.');
      setError(msg);
      toast.error(msg);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { data, isLoading, error, execute, reset };
}

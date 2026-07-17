'use client';

import { useCallback, useEffect, useState } from 'react';

export type ClipboardCopyStatus = 'idle' | 'copied' | 'error';

/**
 * 클립보드 복사 결과와 짧은 사용자 피드백 수명을 한곳에서 관리합니다.
 * key를 전달하면 목록에서 마지막으로 복사한 항목도 함께 식별할 수 있습니다.
 */
export function useClipboardCopy<Key = never>(resetAfterMs = 2_000) {
  const [result, setResult] = useState<{
    status: Exclude<ClipboardCopyStatus, 'idle'>;
    key: Key | null;
  } | null>(null);

  const copy = useCallback(async (text: string, key: Key | null = null): Promise<boolean> => {
    if (typeof navigator === 'undefined' || typeof navigator.clipboard?.writeText !== 'function') {
      setResult({ status: 'error', key });
      return false;
    }

    try {
      await navigator.clipboard.writeText(text);
      setResult({ status: 'copied', key });
      return true;
    } catch {
      setResult({ status: 'error', key });
      return false;
    }
  }, []);

  useEffect(() => {
    if (!result) return;
    const timer = window.setTimeout(() => setResult(null), resetAfterMs);
    return () => window.clearTimeout(timer);
  }, [resetAfterMs, result]);

  return {
    copy,
    status: result?.status ?? 'idle',
    activeKey: result?.key ?? null,
  } as const;
}

'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  copyItemsToClipboard,
  copyTextToClipboard,
  type ClipboardItemsSource,
  type ClipboardOperationResult,
  type ClipboardTextSource,
} from '@/lib/clipboard';

export type ClipboardCopyStatus = 'idle' | 'copied' | 'error';

export type ClipboardCopyResult = ClipboardOperationResult;

interface UseClipboardCopyOptions {
  resetDelayMs?: number;
}

const DEFAULT_RESET_DELAY_MS = 2_000;

export function useClipboardCopy(
  { resetDelayMs = DEFAULT_RESET_DELAY_MS }: UseClipboardCopyOptions = {},
) {
  const [status, setStatus] = useState<ClipboardCopyStatus>('idle');
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIdRef = useRef(0);
  const mountedRef = useRef(true);

  const clearResetTimer = useCallback(() => {
    if (resetTimerRef.current !== null) {
      clearTimeout(resetTimerRef.current);
      resetTimerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    requestIdRef.current += 1;
    clearResetTimer();
    if (mountedRef.current) {
      setStatus('idle');
      setActiveKey(null);
    }
  }, [clearResetTimer]);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      reset();
    };
  }, [reset]);

  const showFeedback = useCallback((
    nextStatus: Exclude<ClipboardCopyStatus, 'idle'>,
    key: string | null,
    requestId: number,
  ) => {
    if (!mountedRef.current || requestId !== requestIdRef.current) return;

    setStatus(nextStatus);
    setActiveKey(key);
    resetTimerRef.current = setTimeout(() => {
      resetTimerRef.current = null;
      if (mountedRef.current && requestId === requestIdRef.current) {
        setStatus('idle');
        setActiveKey(null);
      }
    }, resetDelayMs);
  }, [resetDelayMs]);

  const runCopy = useCallback(async (
    operation: (isCurrent: () => boolean) => Promise<ClipboardOperationResult>,
    key?: string,
  ): Promise<ClipboardCopyResult> => {
    reset();
    const requestId = requestIdRef.current;
    const isCurrentRequest = () => (
      mountedRef.current && requestId === requestIdRef.current
    );

    let operationResult: ClipboardOperationResult;
    try {
      operationResult = await operation(isCurrentRequest);
    } catch {
      operationResult = { copied: false, isCurrent: true };
    }

    const isCurrent = isCurrentRequest() && operationResult.isCurrent;
    if (isCurrent) {
      showFeedback(operationResult.copied ? 'copied' : 'error', key ?? null, requestId);
    }

    return { copied: operationResult.copied, isCurrent };
  }, [reset, showFeedback]);

  const copyText = useCallback((
    text: ClipboardTextSource,
    key?: string,
  ): Promise<ClipboardCopyResult> => runCopy(
    (isCurrent) => copyTextToClipboard(text, { shouldContinue: isCurrent }),
    key,
  ), [runCopy]);

  const copyItems = useCallback((
    items: ClipboardItemsSource,
    key?: string,
  ): Promise<ClipboardCopyResult> => runCopy(
    (isCurrent) => copyItemsToClipboard(items, { shouldContinue: isCurrent }),
    key,
  ), [runCopy]);

  return { status, activeKey, copyText, copyItems, reset };
}

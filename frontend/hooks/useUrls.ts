'use client';

import { useState, useCallback, useEffect } from 'react';
import { useAuthUserId } from '@/hooks/useAuthUserId';
import { getAuthSession } from '@/lib/auth-session';

const MAX_URLS = 10;

/** http/https URL 기본 검증 (YouTube, 웹페이지, RSS, arXiv 모두 허용) */
const VALID_URL_REGEX = /^https?:\/\/.+/i;
const EMPTY_URLS: string[] = [];

interface AccountUrlState {
  ownerId: string | null;
  urls: string[];
}

function currentAuthUserId(): string | null {
  return getAuthSession()?.user.id ?? null;
}

export function useUrls() {
  const authUserId = useAuthUserId();
  const [state, setState] = useState<AccountUrlState>(() => ({
    ownerId: authUserId,
    urls: [],
  }));
  const urls = state.ownerId === authUserId ? state.urls : EMPTY_URLS;

  useEffect(() => {
    // 계정이 바뀌는 렌더에서는 위의 EMPTY_URLS를 즉시 노출하고,
    // effect에서 새 계정의 빈 큐를 상태의 소유자로 확정한다.
    setState((current) => {
      if (currentAuthUserId() !== authUserId || current.ownerId === authUserId) {
        return current;
      }
      return { ownerId: authUserId, urls: [] };
    });
  }, [authUserId]);

  const updateUrls = useCallback((updater: (current: string[]) => string[]) => {
    if (currentAuthUserId() !== authUserId) return;
    setState((current) => {
      if (currentAuthUserId() !== authUserId) return current;
      const currentUrls = current.ownerId === authUserId ? current.urls : EMPTY_URLS;
      const nextUrls = updater(currentUrls);
      if (current.ownerId === authUserId && nextUrls === currentUrls) return current;
      return { ownerId: authUserId, urls: nextUrls };
    });
  }, [authUserId]);

  const addUrl = useCallback((url: string): string | null => {
    const trimmed = url.trim();
    if (!trimmed) return 'URL을 입력해주세요.';
    if (!VALID_URL_REGEX.test(trimmed)) return '유효한 URL이 아닙니다. (http:// 또는 https://)';
    if (urls.includes(trimmed)) return '이미 추가된 URL입니다.';
    if (urls.length >= MAX_URLS) return `최대 ${MAX_URLS}개까지 추가할 수 있습니다.`;
    updateUrls((prev) => {
      if (prev.includes(trimmed) || prev.length >= MAX_URLS) return prev;
      return [...prev, trimmed];
    });
    return null;
  }, [urls, updateUrls]);

  const addUrls = useCallback((newUrls: string[]): { added: number; errors: string[] } => {
    const errors: string[] = [];
    let added = 0;
    updateUrls((prev) => {
      const result = [...prev];
      for (const url of newUrls) {
        const trimmed = url.trim();
        if (!trimmed) continue;
        if (!VALID_URL_REGEX.test(trimmed)) { errors.push(trimmed); continue; }
        if (result.includes(trimmed)) continue;
        if (result.length >= MAX_URLS) break;
        result.push(trimmed);
        added++;
      }
      return result;
    });
    return { added, errors };
  }, [updateUrls]);

  const removeUrl = useCallback((url: string) => {
    updateUrls((prev) => prev.filter((u) => u !== url));
  }, [updateUrls]);

  const clearUrls = useCallback(() => {
    updateUrls(() => []);
  }, [updateUrls]);

  const reorderUrls = useCallback((from: number, to: number) => {
    updateUrls((prev) => {
      if (from < 0 || from >= prev.length || to < 0 || to >= prev.length) return prev;
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
  }, [updateUrls]);

  return { urls, addUrl, addUrls, removeUrl, clearUrls, reorderUrls };
}

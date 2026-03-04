'use client';

import { useState, useCallback } from 'react';

const MAX_URLS = 10;

/** http/https URL 기본 검증 (YouTube, 웹페이지, RSS, arXiv 모두 허용) */
const VALID_URL_REGEX = /^https?:\/\/.+/i;

export function useUrls() {
  const [urls, setUrls] = useState<string[]>([]);

  const addUrl = useCallback((url: string): string | null => {
    const trimmed = url.trim();
    if (!trimmed) return 'URL을 입력해주세요.';
    if (!VALID_URL_REGEX.test(trimmed)) return '유효한 URL이 아닙니다. (http:// 또는 https://)';
    if (urls.includes(trimmed)) return '이미 추가된 URL입니다.';
    if (urls.length >= MAX_URLS) return `최대 ${MAX_URLS}개까지 추가할 수 있습니다.`;
    setUrls((prev) => [...prev, trimmed]);
    return null;
  }, [urls]);

  const addUrls = useCallback((newUrls: string[]): { added: number; errors: string[] } => {
    const errors: string[] = [];
    let added = 0;
    setUrls((prev) => {
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
  }, []);

  const removeUrl = useCallback((url: string) => {
    setUrls((prev) => prev.filter((u) => u !== url));
  }, []);

  const clearUrls = useCallback(() => {
    setUrls([]);
  }, []);

  const reorderUrls = useCallback((from: number, to: number) => {
    setUrls((prev) => {
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
  }, []);

  return { urls, addUrl, addUrls, removeUrl, clearUrls, reorderUrls };
}

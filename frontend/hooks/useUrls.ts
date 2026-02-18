'use client';

import { useState, useCallback } from 'react';
import { YOUTUBE_URL_REGEX } from '@/lib/constants';

const MAX_URLS = 10;

export function useUrls() {
  const [urls, setUrls] = useState<string[]>([]);

  const addUrl = useCallback((url: string): string | null => {
    const trimmed = url.trim();
    if (!trimmed) return 'URL을 입력해주세요.';
    if (!YOUTUBE_URL_REGEX.test(trimmed)) return '유효한 YouTube URL이 아닙니다.';
    if (urls.includes(trimmed)) return '이미 추가된 URL입니다.';
    if (urls.length >= MAX_URLS) return `최대 ${MAX_URLS}개까지 추가할 수 있습니다.`;
    setUrls((prev) => [...prev, trimmed]);
    return null;
  }, [urls]);

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

  return { urls, addUrl, removeUrl, clearUrls, reorderUrls };
}

'use client';

import { useState, useCallback, useRef } from 'react';

const MAX_URLS = 10;
const TRACKING_PARAM = /^(utm_.+|fbclid|gclid|dclid|msclkid)$/i;

/**
 * 동일 콘텐츠 URL 비교/저장용 정규화.
 * - scheme/host 대소문자 및 기본 포트는 URL 표준화에 위임
 * - 문서 내 fragment와 광고 추적 파라미터 제거
 * - query 순서 정렬, 루트 외 trailing slash 제거
 */
export function canonicalizeUrl(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;

    parsed.hash = '';
    for (const key of [...parsed.searchParams.keys()]) {
      if (TRACKING_PARAM.test(key)) parsed.searchParams.delete(key);
    }
    parsed.searchParams.sort();

    if (parsed.pathname.length > 1) {
      parsed.pathname = parsed.pathname.replace(/\/+$/, '');
    }
    return parsed.toString();
  } catch {
    return null;
  }
}

export function useUrls() {
  const [urls, setUrls] = useState<string[]>([]);
  // React state 커밋 전 같은 이벤트 루프에서 연속 addUrl이 호출돼도 중복을 막는다.
  const urlsRef = useRef<string[]>([]);

  const commitUrls = useCallback((next: string[]) => {
    urlsRef.current = next;
    setUrls(next);
  }, []);

  const addUrl = useCallback((url: string): string | null => {
    const trimmed = url.trim();
    if (!trimmed) return 'URL을 입력해주세요.';
    const canonical = canonicalizeUrl(trimmed);
    if (!canonical) return '유효한 URL이 아닙니다. (http:// 또는 https://)';

    const current = urlsRef.current;
    if (current.includes(canonical)) return '이미 추가된 URL입니다.';
    if (current.length >= MAX_URLS) return `최대 ${MAX_URLS}개까지 추가할 수 있습니다.`;

    commitUrls([...current, canonical]);
    return null;
  }, [commitUrls]);

  const addUrls = useCallback((newUrls: string[]): { added: number; errors: string[] } => {
    const errors: string[] = [];
    let added = 0;
    const result = [...urlsRef.current];

    for (const url of newUrls) {
      const trimmed = url.trim();
      if (!trimmed) continue;
      const canonical = canonicalizeUrl(trimmed);
      if (!canonical) {
        errors.push(trimmed);
        continue;
      }
      if (result.includes(canonical)) continue;
      if (result.length >= MAX_URLS) break;
      result.push(canonical);
      added += 1;
    }

    if (added > 0) commitUrls(result);
    return { added, errors };
  }, [commitUrls]);

  const removeUrl = useCallback((url: string) => {
    const canonical = canonicalizeUrl(url) || url;
    commitUrls(urlsRef.current.filter((u) => u !== canonical));
  }, [commitUrls]);

  const clearUrls = useCallback(() => {
    commitUrls([]);
  }, [commitUrls]);

  const reorderUrls = useCallback((from: number, to: number) => {
    const next = [...urlsRef.current];
    const [item] = next.splice(from, 1);
    if (item === undefined) return;
    next.splice(to, 0, item);
    commitUrls(next);
  }, [commitUrls]);

  return { urls, addUrl, addUrls, removeUrl, clearUrls, reorderUrls };
}

'use client';

import { useState, useEffect, useRef } from 'react';
import { getMcpPlugins } from '@/lib/api';
import type { McpPlugin } from '@/lib/types';

// 모듈 레벨 캐시 — 한 번 로드하면 모든 컴포넌트에서 공유
let cachedPlugins: McpPlugin[] | null = null;

/**
 * MCP 플러그인 목록을 로드하는 훅.
 * 최초 1회만 API를 호출하고 이후에는 캐시를 반환합니다.
 *
 * @param enabled - false이면 API 호출을 건너뜁니다 (예: 모달이 닫혀있을 때)
 */
export function useMcpPlugins(enabled = true) {
  const [plugins, setPlugins] = useState<McpPlugin[]>(cachedPlugins || []);
  const fetched = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    if (cachedPlugins) {
      setPlugins(cachedPlugins);
      return;
    }
    if (fetched.current) return;
    fetched.current = true;

    getMcpPlugins()
      .then((res) => {
        cachedPlugins = res.plugins;
        setPlugins(res.plugins);
      })
      .catch(() => {});
  }, [enabled]);

  return plugins;
}

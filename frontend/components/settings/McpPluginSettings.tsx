'use client';

import { useEffect, useState } from 'react';
import { getMcpPlugins } from '@/lib/api';
import type { McpPlugin } from '@/lib/types';

export default function McpPluginSettings() {
  const [plugins, setPlugins] = useState<McpPlugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMcpPlugins()
      .then((res) => setPlugins(res.plugins))
      .catch((err) => setError(err instanceof Error ? err.message : '플러그인 목록 조회 실패'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <p className="text-sm text-muted-foreground">플러그인 로딩 중...</p>;
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  if (plugins.length === 0) {
    return <p className="text-sm text-muted-foreground">등록된 플러그인이 없습니다.</p>;
  }

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-muted-foreground block">
        발행 플러그인
      </label>
      {plugins.map((plugin) => (
        <div
          key={plugin.id}
          className="flex items-center justify-between p-3 rounded-lg border border-border bg-background"
        >
          <div>
            <div className="text-sm font-medium">{plugin.name}</div>
            <div className="text-xs text-muted-foreground">{plugin.description}</div>
          </div>
          <span className="text-xs text-muted-foreground px-2 py-1 rounded-full bg-muted">
            대기
          </span>
        </div>
      ))}
    </div>
  );
}

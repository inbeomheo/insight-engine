'use client';

import { memo, useState, useEffect, useCallback } from 'react';
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { RefreshCw, XCircle, RotateCcw, Loader2 } from 'lucide-react';
import type { PublishQueueItem } from '@/lib/types';

/** 상태별 배지 스타일 */
const STATUS_CONFIG: Record<
  PublishQueueItem['status'],
  { label: string; className: string; pulse?: boolean }
> = {
  queued: {
    label: '대기',
    className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  },
  publishing: {
    label: '발행 중',
    className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
    pulse: true,
  },
  success: {
    label: '완료',
    className: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
  },
  failed: {
    label: '실패',
    className: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  },
};

/** ISO 날짜 → 상대 시간 표시 */
function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return '방금 전';
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}분 전`;
  const hour = Math.floor(min / 60);
  if (hour < 24) return `${hour}시간 전`;
  const day = Math.floor(hour / 24);
  return `${day}일 전`;
}

const AUTO_REFRESH_INTERVAL = 30_000; // 30초

export const PublishQueue = memo(function PublishQueue() {
  const [items, setItems] = useState<PublishQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await fetch('/api/publish-queue');
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setItems(data.items ?? []);
        setError(null);
      }
    } catch {
      setError('발행 큐를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  }, []);

  // 초기 로드 + 30초 자동 갱신
  useEffect(() => {
    fetchQueue();
    const timer = setInterval(fetchQueue, AUTO_REFRESH_INTERVAL);
    return () => clearInterval(timer);
  }, [fetchQueue]);

  /** 항목 취소 */
  const handleCancel = useCallback(async (itemId: string) => {
    setActionLoading(itemId);
    try {
      const res = await fetch(`/api/publish-queue/${itemId}/cancel`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        // 취소된 항목 제거
        setItems(prev => prev.filter(i => i.id !== itemId));
      }
    } finally {
      setActionLoading(null);
    }
  }, []);

  /** 실패 항목 재시도 */
  const handleRetry = useCallback(async (itemId: string) => {
    setActionLoading(itemId);
    try {
      const res = await fetch(`/api/publish-queue/${itemId}/retry`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        await fetchQueue();
      }
    } finally {
      setActionLoading(null);
    }
  }, [fetchQueue]);

  if (loading) {
    return (
      <div className="text-center py-12 text-zinc-500">
        <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
        로딩 중...
      </div>
    );
  }

  if (error) {
    return <div className="text-center py-12 text-red-500">{error}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">발행 큐</h2>
        <Button variant="ghost" size="sm" onClick={fetchQueue}>
          <RefreshCw className="h-4 w-4 mr-1" />
          새로고침
        </Button>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-12 text-zinc-500">
          발행 큐가 비어 있습니다.
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>제목</TableHead>
              <TableHead>플러그인</TableHead>
              <TableHead>상태</TableHead>
              <TableHead className="text-center">재시도</TableHead>
              <TableHead>생성 시간</TableHead>
              <TableHead className="text-right">작업</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => {
              const cfg = STATUS_CONFIG[item.status];
              const isActioning = actionLoading === item.id;
              return (
                <TableRow key={item.id}>
                  <TableCell className="max-w-[200px] truncate font-medium">
                    {item.status === 'success' && item.published_url ? (
                      <a
                        href={item.published_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline dark:text-blue-400"
                      >
                        {item.title}
                      </a>
                    ) : (
                      item.title
                    )}
                  </TableCell>
                  <TableCell className="text-zinc-500">
                    {item.plugin_id}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn(
                        cfg.className,
                        cfg.pulse && 'animate-pulse',
                      )}
                    >
                      {cfg.label}
                    </Badge>
                    {item.error_message && (
                      <p className="text-xs text-red-500 mt-1 max-w-[180px] truncate">
                        {item.error_message}
                      </p>
                    )}
                  </TableCell>
                  <TableCell className="text-center">
                    {item.retry_count > 0 ? `${item.retry_count}/3` : '-'}
                  </TableCell>
                  <TableCell className="text-zinc-500 text-xs">
                    {formatRelative(item.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    {item.status === 'queued' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isActioning}
                        onClick={() => handleCancel(item.id)}
                      >
                        {isActioning ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <XCircle className="h-4 w-4" />
                        )}
                        <span className="ml-1">취소</span>
                      </Button>
                    )}
                    {item.status === 'failed' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isActioning}
                        onClick={() => handleRetry(item.id)}
                      >
                        {isActioning ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RotateCcw className="h-4 w-4" />
                        )}
                        <span className="ml-1">재시도</span>
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}
    </div>
  );
});

export default PublishQueue;

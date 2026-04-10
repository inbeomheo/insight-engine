'use client';

import { useCallback, useState, useMemo } from 'react';
import { useResultStore } from '@/stores/resultStore';


const PAGE_SIZE = 20;

/** 무한 스크롤 히스토리 훅 (F5-08) — 클라이언트 사이드 페이지네이션 */
export function useInfiniteHistory() {
  const [page, setPage] = useState(1);
  const filteredReports = useResultStore((s) => s.filteredReports);

  const allReports = useMemo(() => filteredReports(), [filteredReports]);

  const data = useMemo(
    () => allReports.slice(0, page * PAGE_SIZE),
    [allReports, page],
  );

  const hasNextPage = data.length < allReports.length;

  const fetchNextPage = useCallback(() => {
    if (hasNextPage) {
      setPage((p) => p + 1);
    }
  }, [hasNextPage]);

  const reset = useCallback(() => {
    setPage(1);
  }, []);

  return {
    data,
    hasNextPage,
    fetchNextPage,
    total: allReports.length,
    reset,
  };
}

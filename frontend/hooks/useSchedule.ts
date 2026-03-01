'use client';

import { useState, useCallback, useEffect } from 'react';
import { createSchedule, getSchedules, deleteSchedule } from '@/lib/api';
import { toast } from 'sonner';
import type { ScheduledPost } from '@/lib/types';

export function useSchedule() {
  const [schedules, setSchedules] = useState<ScheduledPost[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchSchedules = useCallback(async () => {
    try {
      const res = await getSchedules();
      setSchedules(res.schedules);
    } catch {
      // 인증 없이 사용 시 조용히 실패
    }
  }, []);

  const addSchedule = useCallback(
    async (data: {
      title: string;
      content: string;
      html?: string;
      target_plugin: string;
      scheduled_at: string;
    }) => {
      setIsLoading(true);
      try {
        const post = await createSchedule(data);
        setSchedules((prev) => [post, ...prev]);
        toast.success('예약이 등록되었습니다');
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '예약 등록 실패';
        toast.error(message);
        return false;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const removeSchedule = useCallback(async (postId: string) => {
    try {
      await deleteSchedule(postId);
      setSchedules((prev) => prev.filter((s) => s.id !== postId));
      toast.success('예약이 삭제되었습니다');
    } catch {
      toast.error('예약 삭제 실패');
    }
  }, []);

  // 초기 로드
  useEffect(() => {
    fetchSchedules();
  }, [fetchSchedules]);

  return { schedules, isLoading, addSchedule, removeSchedule, refetch: fetchSchedules };
}

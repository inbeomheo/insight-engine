'use client';

import { useState, useCallback } from 'react';
import { generateMindmap } from '@/lib/api';
import { useResultStore } from '@/stores/resultStore';
import { toast } from 'sonner';

export function useMindmap() {
  const [loading, setLoading] = useState(false);
  const [markdown, setMarkdown] = useState('');
  const { updateReport, reports } = useResultStore();

  const generate = useCallback(
    async (reportId: string) => {
      const report = reports.find((r) => r.id === reportId);
      if (!report) return;

      // 캐시 확인
      if (report.mindmapMarkdown) {
        setMarkdown(report.mindmapMarkdown);
        return;
      }

      setLoading(true);
      try {
        const res = await generateMindmap(report.content, report.title);
        setMarkdown(res.markdown);
        updateReport(reportId, { mindmapMarkdown: res.markdown });
      } catch {
        toast.error('마인드맵 생성 실패');
      } finally {
        setLoading(false);
      }
    },
    [reports, updateReport]
  );

  return { loading, markdown, generate };
}

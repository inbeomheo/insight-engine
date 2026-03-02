'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Brain, Loader2 } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { generateMindmap } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';

export default function MindmapModal() {
  const { activeModal, activeMindmapReportId, setMindmapModalOpen } = useUIStore();
  const mindmapModalOpen = activeModal === 'mindmap';
  const { reports, updateReport } = useResultStore();
  const { selectedModel } = useSettingsStore();
  const [loading, setLoading] = useState(false);
  const [markdown, setMarkdown] = useState('');

  const report = reports.find((r) => r.id === activeMindmapReportId);

  useEffect(() => {
    if (!mindmapModalOpen || !report) return;

    // 캐시된 마인드맵이 있으면 사용
    if (report.mindmapMarkdown) {
      setMarkdown(report.mindmapMarkdown);
      return;
    }

    // 새로 생성
    setLoading(true);
    generateMindmap(report.content, report.title, selectedModel)
      .then((res) => {
        setMarkdown(res.markdown);
        updateReport(report.id, { mindmapMarkdown: res.markdown });
      })
      .catch(() => toast.error('마인드맵 생성 실패'))
      .finally(() => setLoading(false));
  }, [mindmapModalOpen, report, updateReport]);

  return (
    <Dialog open={mindmapModalOpen} onOpenChange={(v) => setMindmapModalOpen(v)}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            마인드맵
          </DialogTitle>
          <DialogDescription>콘텐츠를 구조화된 마인드맵으로 확인합니다</DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 max-h-[70vh]">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-sm text-muted-foreground">마인드맵 생성 중...</span>
            </div>
          ) : (
            <div className="prose max-w-none p-4">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

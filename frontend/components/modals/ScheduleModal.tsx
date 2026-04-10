'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Calendar, Clock, Send } from 'lucide-react';
import { useMcpPlugins } from '@/hooks/useMcpPlugins';

interface ScheduleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  content: string;
  html?: string;
  onSchedule: (data: { target_plugin: string; scheduled_at: string }) => void;
  isLoading?: boolean;
}

export default function ScheduleModal({
  open,
  onOpenChange,
  title,
  content,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  html,
  onSchedule,
  isLoading,
}: ScheduleModalProps) {
  const plugins = useMcpPlugins(open);
  const [selectedPlugin, setSelectedPlugin] = useState('');
  const [scheduledAt, setScheduledAt] = useState('');

  function formatLocalDatetime(date: Date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    return `${y}-${m}-${d}T${h}:${min}`;
  }

  /* eslint-disable react-hooks/set-state-in-effect */
  // 플러그인 로드 후 기본 선택
  useEffect(() => {
    if (plugins.length > 0 && !selectedPlugin) {
      setSelectedPlugin(plugins[0].id);
    }
  }, [plugins, selectedPlugin]);

  // 모달 열릴 때 기본값 초기화: 내일 오전 9시
  useEffect(() => {
    if (!open) return;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(9, 0, 0, 0);
    setScheduledAt(formatLocalDatetime(tomorrow));
  }, [open]);
  /* eslint-enable react-hooks/set-state-in-effect */

  function handleSubmit() {
    if (!selectedPlugin || !scheduledAt) return;
    const isoDate = new Date(scheduledAt).toISOString();
    onSchedule({ target_plugin: selectedPlugin, scheduled_at: isoDate });
  }

  const canSubmit = selectedPlugin && scheduledAt && !isLoading;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary" />
            예약 발행
          </DialogTitle>
          <DialogDescription>콘텐츠를 지정 시간에 자동 발행합니다</DialogDescription>
        </DialogHeader>

        {/* 미리보기 */}
        <div className="rounded-lg bg-muted p-3">
          <p className="text-sm font-medium truncate">{title}</p>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
            {content.slice(0, 150)}...
          </p>
        </div>

        {/* 플러그인 선택 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">발행 대상</label>
          {plugins.length === 0 ? (
            <p className="text-sm text-muted-foreground">등록된 플러그인이 없습니다</p>
          ) : (
            <select
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={selectedPlugin}
              onChange={(e) => setSelectedPlugin(e.target.value)}
            >
              {plugins.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* 날짜/시간 선택 */}
        <div className="space-y-2">
          <label className="text-sm font-medium flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            예약 시간
          </label>
          <input
            type="datetime-local"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            value={scheduledAt}
            onChange={(e) => setScheduledAt(e.target.value)}
          />
        </div>

        {/* 제출 */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            취소
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            <Send className="h-4 w-4 mr-1.5" />
            {isLoading ? '등록 중...' : '예약 등록'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

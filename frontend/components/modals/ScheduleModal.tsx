'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Calendar } from 'lucide-react';

// html/onSchedule/isLoading은 현재 미사용 — Dep-6(예약 발행 재설계)에서 이 prop 계약 자체를 정리 예정
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
}: ScheduleModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary" />
            예약 발행
          </DialogTitle>
          <DialogDescription>발행 기능이 종료되었습니다.</DialogDescription>
        </DialogHeader>

        {/* 미리보기 */}
        <div className="rounded-lg bg-muted p-3">
          <p className="text-sm font-medium truncate">{title}</p>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
            {content.slice(0, 150)}...
          </p>
        </div>

        <p className="text-sm text-muted-foreground">
          발행 기능이 종료되어 예약 발행을 새로 등록할 수 없습니다.
        </p>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            닫기
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

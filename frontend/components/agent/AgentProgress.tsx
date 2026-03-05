'use client';

import { cn } from '@/lib/utils';

interface AgentEvent {
  phase: string;
  message: string;
  data: Record<string, unknown>;
  iteration: number;
  progress: number;
  timestamp: number;
}

interface AgentProgressProps {
  events: AgentEvent[];
  isRunning: boolean;
  className?: string;
}

const PHASE_LABELS: Record<string, string> = {
  plan: '계획 수립',
  execute: '실행',
  reflect: '평가',
  done: '완료',
  error: '오류',
};

const PHASE_COLORS: Record<string, string> = {
  plan: 'text-blue-500',
  execute: 'text-yellow-500',
  reflect: 'text-purple-500',
  done: 'text-green-500',
  error: 'text-red-500',
};

export default function AgentProgress({ events, isRunning, className }: AgentProgressProps) {
  if (events.length === 0 && !isRunning) return null;

  const latestEvent = events[events.length - 1];
  const progress = latestEvent?.progress ?? 0;

  return (
    <div className={cn('rounded-lg border p-4 space-y-3', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">에이전트 진행 상황</h3>
        {isRunning && (
          <span className="text-xs text-muted-foreground animate-pulse">실행 중...</span>
        )}
      </div>

      {/* 프로그레스 바 */}
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-500 rounded-full"
          style={{ width: `${Math.round(progress * 100)}%` }}
        />
      </div>

      {/* 이벤트 로그 */}
      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {events.map((event, idx) => (
          <div key={idx} className="flex items-start gap-2 text-xs">
            <span className={cn('font-medium shrink-0', PHASE_COLORS[event.phase] ?? 'text-muted-foreground')}>
              [{PHASE_LABELS[event.phase] ?? event.phase}]
            </span>
            <span className="text-muted-foreground">{event.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

'use client';

import type { PipelineStep } from '@/lib/types';

interface PipelineProgressProps {
  steps: PipelineStep[];
  progress: number;
  isRunning: boolean;
  error: string | null;
}

function StepIcon({ status }: { status: PipelineStep['status'] }) {
  if (status === 'done') {
    return <span className="text-green-400">{'\u2713'}</span>;
  }
  if (status === 'running') {
    return (
      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-[var(--accent-primary)] border-t-transparent" />
    );
  }
  if (status === 'error') {
    return <span className="text-red-400">{'\u2717'}</span>;
  }
  return <span className="text-[var(--text-tertiary)]">{'\u25CB'}</span>;
}

export default function PipelineProgress({ steps, progress, isRunning, error }: PipelineProgressProps) {
  if (!isRunning && progress === 0 && !error) return null;

  const pct = Math.round(progress * 100);

  return (
    <div className="my-4 rounded-lg border border-[var(--border-primary)] p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-medium">
          {isRunning ? '파이프라인 실행 중...' : error ? '파이프라인 오류' : '파이프라인 완료'}
        </p>
        <span className="text-xs text-[var(--text-tertiary)]">{pct}%</span>
      </div>

      {/* 진행률 바 */}
      <div className="mb-3 h-1.5 w-full overflow-hidden rounded-full bg-[var(--background-tertiary)]">
        <div
          className="h-full rounded-full bg-[var(--accent-primary)] transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* 스텝 목록 */}
      <div className="space-y-1.5">
        {steps.map((step, i) => (
          <div key={step.id} className="flex items-center gap-2 text-sm">
            <span className="flex w-5 items-center justify-center text-xs text-[var(--text-tertiary)]">
              {i + 1}.
            </span>
            <span className="flex w-4 items-center justify-center">
              <StepIcon status={step.status} />
            </span>
            <span
              className={
                step.status === 'done' || step.status === 'running'
                  ? 'text-[var(--text-primary)]'
                  : step.status === 'error'
                    ? 'text-red-400'
                    : 'text-[var(--text-tertiary)]'
              }
            >
              {step.name}
            </span>
            {step.elapsed != null && step.status === 'done' && (
              <span className="text-xs text-[var(--text-tertiary)]">({step.elapsed}s)</span>
            )}
            {step.error && (
              <span className="text-xs text-red-400">{step.error}</span>
            )}
          </div>
        ))}
      </div>

      {/* 전체 에러 메시지 */}
      {error && (
        <p className="mt-3 text-sm text-red-400">{error}</p>
      )}
    </div>
  );
}

'use client';

import { memo, type KeyboardEvent } from 'react';
import { AlignJustify, FileText, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ViewMode } from '@/lib/types';

interface ViewModeSelectorProps {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
}

const MODES: { id: ViewMode; label: string; icon: typeof AlignJustify }[] = [
  { id: 'compact', label: '요약', icon: AlignJustify },
  { id: 'full', label: '전체', icon: FileText },
  { id: 'timeline', label: '타임라인', icon: Clock },
];

/** 결과 카드 뷰 모드 선택기 (Segmented Control) */
export const ViewModeSelector = memo(function ViewModeSelector({ mode, onChange }: ViewModeSelectorProps) {
  function selectMode(nextMode: ViewMode) {
    onChange(nextMode);
    requestAnimationFrame(() => document.getElementById(`result-view-mode-${nextMode}`)?.focus());
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? MODES.length - 1
          : (index + (event.key === 'ArrowRight' ? 1 : -1) + MODES.length) % MODES.length;
    selectMode(MODES[nextIndex].id);
  }

  return (
    <div
      data-testid="result-view-mode-selector"
      className="inline-flex rounded-lg border border-zinc-200 dark:border-zinc-700 p-0.5 bg-zinc-100 dark:bg-zinc-800"
      role="radiogroup"
      aria-label="뷰 모드 선택"
    >
      {MODES.map(({ id, label, icon: Icon }, index) => (
        <button
          key={id}
          id={`result-view-mode-${id}`}
          data-testid={`result-view-mode-${id}`}
          onClick={() => selectMode(id)}
          onKeyDown={(event) => handleKeyDown(event, index)}
          role="radio"
          aria-checked={mode === id}
          aria-label={`${label} 뷰 모드`}
          tabIndex={mode === id ? 0 : -1}
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-all',
            mode === id
              ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm'
              : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300',
          )}
        >
          <Icon className="h-3.5 w-3.5" />
          {label}
        </button>
      ))}
    </div>
  );
});

export default ViewModeSelector;

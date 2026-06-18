'use client';

import { memo } from 'react';
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
  return (
    <div
      className="inline-flex rounded-full border border-border bg-muted p-1"
      role="radiogroup"
      aria-label="뷰 모드 선택"
    >
      {MODES.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          role="radio"
          aria-checked={mode === id}
          aria-label={`${label} 뷰 모드`}
          className={cn(
            'signal-meta inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-semibold transition-colors',
            mode === id
              ? 'bg-foreground text-background'
              : 'text-muted-foreground hover:text-foreground',
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

'use client';

import { useSettingsStore } from '@/stores/settingsStore';
import type { GenerationMode } from '@/lib/types';
import { cn } from '@/lib/utils';

const modes: Array<{ key: GenerationMode; label: string; shortLabel: string }> = [
  { key: 'individual', label: '개별 분석', shortLabel: '개별' },
  { key: 'combined', label: '합쳐서 분석', shortLabel: '통합' },
  { key: 'fusion', label: '퓨전 분석', shortLabel: '퓨전' },
];

export default function GenerationModeSelector() {
  const { generationMode, setGenerationMode } = useSettingsStore();

  return (
    <div
      className="inline-flex w-full max-w-[360px] gap-1 rounded-full border border-border bg-muted p-1 sm:w-auto"
      role="radiogroup"
      aria-label="생성 모드 선택"
    >
      {modes.map((m) => (
        <button
          key={m.key}
          onClick={() => setGenerationMode(m.key)}
          role="radio"
          aria-checked={generationMode === m.key}
          aria-label={`${m.label} 생성 모드`}
          className={cn(
            'signal-meta min-h-9 flex-1 rounded-full px-3 py-1.5 text-[10px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 sm:min-w-20',
            generationMode === m.key
              ? 'bg-foreground text-background'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          {m.shortLabel}
        </button>
      ))}
    </div>
  );
}

'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';

type DetailLevel = 'brief' | 'standard' | 'deep';

interface DetailPresetProps {
  value: DetailLevel;
  onChange: (level: DetailLevel) => void;
}

const LEVELS: { id: DetailLevel; label: string; desc: string }[] = [
  { id: 'brief', label: '간결', desc: '핵심만' },
  { id: 'standard', label: '기본', desc: '균형' },
  { id: 'deep', label: '상세', desc: '풍부하게' },
];

export const DetailPreset = memo(function DetailPreset({ value, onChange }: DetailPresetProps) {
  return (
    <div className="inline-flex rounded-lg border border-zinc-200 dark:border-zinc-700 p-0.5 bg-zinc-100 dark:bg-zinc-800">
      {LEVELS.map((level) => (
        <button
          key={level.id}
          onClick={() => onChange(level.id)}
          className={cn(
            'px-3 py-1 rounded-md text-xs font-medium transition-all',
            value === level.id
              ? 'bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-100 shadow-sm'
              : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300'
          )}
          title={level.desc}
        >
          {level.label}
        </button>
      ))}
    </div>
  );
});

export default DetailPreset;

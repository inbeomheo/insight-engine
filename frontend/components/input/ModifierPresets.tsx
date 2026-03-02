'use client';

import { memo } from 'react';
import { cn } from '@/lib/utils';

interface ModifierPreset {
  id: string;
  label: string;
  description: string;
  modifiers: { length?: string; writing_style?: string };
}

const PRESETS: ModifierPreset[] = [
  { id: 'quick-casual', label: '빠른 요약', description: '짧고 캐주얼하게', modifiers: { length: 'short', writing_style: 'casual' } },
  { id: 'standard', label: '기본', description: '보통 길이, 대화체', modifiers: { length: 'medium', writing_style: 'conversational' } },
  { id: 'detailed-expert', label: '상세 전문가', description: '길고 전문적으로', modifiers: { length: 'long', writing_style: 'expert' } },
  { id: 'blog-friendly', label: '블로그 친화', description: '보통 길이, 설명체', modifiers: { length: 'medium', writing_style: 'explanatory' } },
];

interface ModifierPresetsProps {
  currentModifiers: { length?: string; writing_style?: string };
  onSelect: (modifiers: { length?: string; writing_style?: string }) => void;
}

export const ModifierPresets = memo(function ModifierPresets({ currentModifiers, onSelect }: ModifierPresetsProps) {
  const isActive = (preset: ModifierPreset) =>
    preset.modifiers.length === currentModifiers.length &&
    preset.modifiers.writing_style === currentModifiers.writing_style;

  return (
    <div className="flex flex-wrap gap-2">
      {PRESETS.map((preset) => (
        <button
          key={preset.id}
          onClick={() => onSelect(preset.modifiers)}
          className={cn(
            'px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
            isActive(preset)
              ? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300 dark:border-blue-400'
              : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:border-zinc-600'
          )}
          title={preset.description}
        >
          {preset.label}
        </button>
      ))}
    </div>
  );
});

export default ModifierPresets;

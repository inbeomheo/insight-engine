'use client';

import { useSettingsStore } from '@/stores/settingsStore';
import type { GenerationMode } from '@/lib/types';

const modes: Array<{ key: GenerationMode; label: string }> = [
  { key: 'individual', label: '개별 분석' },
  { key: 'combined', label: '합쳐서 분석' },
  { key: 'fusion', label: '퓨전 분석' },
];

export default function GenerationModeSelector() {
  const { generationMode, setGenerationMode } = useSettingsStore();

  return (
    <div className="flex gap-1 rounded-lg bg-[var(--surface-secondary)] p-1">
      {modes.map((m) => (
        <button
          key={m.key}
          onClick={() => setGenerationMode(m.key)}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
            generationMode === m.key
              ? 'bg-[var(--accent-primary)] text-white'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

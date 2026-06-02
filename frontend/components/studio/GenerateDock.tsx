'use client';

import { Combine, Layers, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getGenerateLabel, getGenerationModeLabel } from './studioConfig';

interface GenerateDockProps {
  sourceCount: number;
  sourceLabel?: string;
  mode: string;
  isLoading: boolean;
  onGenerate: () => void;
  onGenerateMerged: () => void;
  onGenerateFusion: () => void;
}

export default function GenerateDock({ sourceCount, sourceLabel = '소스 대기', mode, isLoading, onGenerate, onGenerateMerged, onGenerateFusion }: GenerateDockProps) {
  const disabled = sourceCount <= 0 || isLoading;
  const Icon = mode === 'fusion' ? Combine : mode === 'combined' ? Layers : Sparkles;
  const handler = mode === 'fusion' ? onGenerateFusion : mode === 'combined' ? onGenerateMerged : onGenerate;
  const modeLabel = getGenerationModeLabel(mode);
  return (
    <section className="sticky bottom-4 z-20 rounded-[24px] border border-indigo-100 bg-white/90 p-3 shadow-lg shadow-indigo-100/70 backdrop-blur-xl">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold text-indigo-700">Ready to Generate</p>
          <p data-testid="generate-dock-summary" className="text-sm text-slate-500">
            {sourceLabel} · 소스 {sourceCount}개 · 모드 {modeLabel}
          </p>
        </div>
        <Button data-testid="generate-dock-button" disabled={disabled} onClick={handler} className="h-12 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 text-sm font-semibold shadow-md shadow-indigo-200 hover:opacity-95">
          {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Icon className="mr-2 h-4 w-4" />}{getGenerateLabel(sourceCount, mode)}
        </Button>
      </div>
    </section>
  );
}

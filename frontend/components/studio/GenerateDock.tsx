'use client';

import { Combine, Layers, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getGenerateLabel, getGenerationModeLabel } from './studioConfig';
import { cn } from '@/lib/utils';

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
  const requiredSources = mode === 'combined' || mode === 'fusion' ? 2 : 1;
  const disabled = sourceCount < requiredSources || isLoading;
  const sticky = sourceCount > 0 || isLoading;
  const Icon = mode === 'fusion' ? Combine : mode === 'combined' ? Layers : Sparkles;
  const handler = mode === 'fusion' ? onGenerateFusion : mode === 'combined' ? onGenerateMerged : onGenerate;
  const modeLabel = getGenerationModeLabel(mode);
  const statusLabel = isLoading
    ? '생성 중입니다'
    : sourceCount < requiredSources
      ? (requiredSources > 1 ? '소스를 더 추가하세요' : '소스를 추가하세요')
      : '생성 준비 완료';
  const buttonLabel = isLoading ? '생성 중입니다' : getGenerateLabel(sourceCount, mode);
  return (
    <section
      data-testid="generate-dock"
      role="region"
      aria-label="생성 실행"
      aria-busy={isLoading}
      className={cn(
        'rounded-[24px] border border-indigo-100 bg-white/90 p-3 backdrop-blur-xl',
        sticky
          ? 'sticky bottom-4 z-20 shadow-lg shadow-indigo-100/70'
          : 'relative z-0 shadow-sm shadow-slate-200/60',
      )}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p id="generate-dock-status" data-testid="generate-dock-status" role="status" aria-live="polite" className="text-xs font-semibold text-indigo-700">{statusLabel}</p>
          <p id="generate-dock-summary" data-testid="generate-dock-summary" className="text-sm text-slate-500">
            {sourceLabel} · 소스 {sourceCount}개 · 모드 {modeLabel}
          </p>
        </div>
        <Button data-testid="generate-dock-button" aria-label={buttonLabel} aria-describedby="generate-dock-status generate-dock-summary" disabled={disabled} onClick={handler} className="h-12 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 text-sm font-semibold shadow-md shadow-indigo-200 hover:opacity-95">
          {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Icon className="mr-2 h-4 w-4" />}{buttonLabel}
        </Button>
      </div>
    </section>
  );
}

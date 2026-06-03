'use client';

import { Bot, Combine, Cpu, Globe, Layers, MessageSquare, Search, SlidersHorizontal, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { STYLE_OPTIONS, LENGTH_OPTIONS, WRITING_STYLE_OPTIONS, LANGUAGE_OPTIONS } from '@/lib/constants';
import { useSettingsStore } from '@/stores/settingsStore';
import { cn } from '@/lib/utils';

const DETAIL_OPTIONS = [
  { value: 'brief', label: '간단', desc: '핵심만 빠르게' },
  { value: 'standard', label: '표준', desc: '균형 잡힌 결과' },
  { value: 'deep', label: '심층', desc: '맥락과 근거 강화' },
] as const;

type OutputBlueprintSourceMode = 'url' | 'text' | 'file' | 'voice';

interface OutputBlueprintProps {
  sourceMode: OutputBlueprintSourceMode;
  sourceCount: number;
}

const SOURCE_MODE_LABELS: Record<OutputBlueprintSourceMode, string> = {
  url: 'URL',
  text: '텍스트',
  file: '파일',
  voice: '음성',
};

function optionLabel<T extends { value: string; label: string }>(items: T[], value: string) {
  return items.find((item) => item.value === value)?.label ?? value;
}

export default function OutputBlueprint({ sourceMode, sourceCount }: OutputBlueprintProps) {
  const selectedProvider = useSettingsStore((s) => s.selectedProvider);
  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const selectedStyle = useSettingsStore((s) => s.selectedStyle);
  const setSelectedStyle = useSettingsStore((s) => s.setSelectedStyle);
  const generationMode = useSettingsStore((s) => s.generationMode);
  const setGenerationMode = useSettingsStore((s) => s.setGenerationMode);
  const modifiers = useSettingsStore((s) => s.modifiers);
  const setModifiers = useSettingsStore((s) => s.setModifiers);
  const enableWebSearch = useSettingsStore((s) => s.enableWebSearch);
  const setEnableWebSearch = useSettingsStore((s) => s.setEnableWebSearch);
  const enableWebResearch = useSettingsStore((s) => s.enableWebResearch);
  const setEnableWebResearch = useSettingsStore((s) => s.setEnableWebResearch);
  const enableDeepComments = useSettingsStore((s) => s.enableDeepComments);
  const setEnableDeepComments = useSettingsStore((s) => s.setEnableDeepComments);
  const enableAgentMode = useSettingsStore((s) => s.enableAgentMode);
  const setEnableAgentMode = useSettingsStore((s) => s.setEnableAgentMode);
  const detailLevel = useSettingsStore((s) => s.detailLevel);
  const setDetailLevel = useSettingsStore((s) => s.setDetailLevel);

  const modelLabel = selectedModel || selectedProvider || '자동 선택';
  const lengthValue = modifiers.length ?? 'medium';
  const writingStyleValue = modifiers.writing_style ?? 'conversational';
  const languageValue = modifiers.language ?? 'ko';
  const isUrlSource = sourceMode === 'url';
  const isMultiSourceModeAvailable = isUrlSource && sourceCount >= 2;
  const multiSourceModeDisabled = !isMultiSourceModeAvailable;
  const visibleGenerationMode = isMultiSourceModeAvailable ? generationMode : 'individual';
  const sourceModeLabel = SOURCE_MODE_LABELS[sourceMode];
  const modeHint = isUrlSource
    ? (sourceCount < 2 ? 'URL 소스 2개 이상을 추가하면 통합/퓨전을 사용할 수 있습니다. 현재는 개별 생성으로 실행됩니다.' : null)
    : `${sourceModeLabel} 소스는 개별 생성으로 실행됩니다. 통합/퓨전은 URL 소스 2개 이상에서 사용할 수 있습니다.`;
  const handleLengthChange = (value: string) => {
    setModifiers({ length: value as 'short' | 'medium' | 'long' });
  };

  return (
    <section className="rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Output Blueprint</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">무엇으로 만들지 정하세요</h2>
        </div>
        <div data-testid="blueprint-model-summary" className="inline-flex max-w-full items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
          <Cpu className="h-3.5 w-3.5 text-indigo-600" />
          <span className="truncate">모델 {modelLabel}</span>
        </div>
      </div>

      <div data-testid="blueprint-style-options" role="group" aria-label="산출물 스타일" className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {STYLE_OPTIONS.map((style) => (
          <button
            key={style.id}
            type="button"
            data-testid={`blueprint-style-${style.id}`}
            aria-pressed={selectedStyle === style.id}
            onClick={() => setSelectedStyle(style.id)}
            className={cn(
              'rounded-2xl border p-3 text-left transition',
              selectedStyle === style.id
                ? 'border-indigo-500 bg-indigo-50 text-indigo-950 shadow-sm'
                : 'border-slate-200 bg-slate-50/60 hover:border-indigo-200 hover:bg-white',
            )}
          >
            <span className="text-lg">{style.emoji}</span>
            <p className="mt-1 text-sm font-semibold">{style.label}</p>
          </button>
        ))}
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        <div className="rounded-2xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-semibold text-slate-500">제작 모드</p>
          <div className="flex flex-wrap gap-2">
            <Button data-testid="blueprint-mode-individual" aria-pressed={visibleGenerationMode === 'individual'} type="button" size="sm" variant={visibleGenerationMode === 'individual' ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setGenerationMode('individual')}><Sparkles className="h-3.5 w-3.5" />개별</Button>
            <Button data-testid="blueprint-mode-combined" aria-pressed={visibleGenerationMode === 'combined'} aria-describedby={modeHint ? 'blueprint-mode-hint' : undefined} disabled={multiSourceModeDisabled} type="button" size="sm" variant={visibleGenerationMode === 'combined' ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setGenerationMode('combined')}><Layers className="h-3.5 w-3.5" />통합</Button>
            <Button data-testid="blueprint-mode-fusion" aria-pressed={visibleGenerationMode === 'fusion'} aria-describedby={modeHint ? 'blueprint-mode-hint' : undefined} disabled={multiSourceModeDisabled} type="button" size="sm" variant={visibleGenerationMode === 'fusion' ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setGenerationMode('fusion')}><Combine className="h-3.5 w-3.5" />퓨전</Button>
          </div>
          {modeHint && (
            <p id="blueprint-mode-hint" data-testid="blueprint-mode-hint" className="mt-2 rounded-xl bg-indigo-50 px-3 py-2 text-[11px] leading-relaxed text-indigo-700">
              {modeHint}
            </p>
          )}
        </div>

        <div data-testid="blueprint-modifier-controls" role="group" aria-label="길이 · 톤 · 언어" className="rounded-2xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-semibold text-slate-500">길이 · 톤 · 언어</p>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <select data-testid="blueprint-length-select" aria-label="길이" className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={lengthValue} onInput={(event) => handleLengthChange(event.currentTarget.value)} onChange={(event) => handleLengthChange(event.currentTarget.value)}>{LENGTH_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
            <select data-testid="blueprint-tone-select" aria-label="톤" className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={writingStyleValue} onChange={(e) => setModifiers({ writing_style: e.target.value as typeof writingStyleValue })}>{WRITING_STYLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
            <select data-testid="blueprint-language-select" aria-label="언어" className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={languageValue} onChange={(e) => setModifiers({ language: e.target.value as 'ko' | 'en' | 'ja' })}>{LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
          </div>
        </div>

        <div data-testid="blueprint-detail-level" role="group" aria-label="상세도" className="rounded-2xl bg-slate-50 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-500"><SlidersHorizontal className="h-3.5 w-3.5" />상세도</p>
          <div className="grid grid-cols-3 gap-1.5">
            {DETAIL_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                data-testid={`blueprint-detail-${option.value}`}
                aria-pressed={detailLevel === option.value}
                className={cn(
                  'rounded-xl border px-2 py-2 text-left text-[11px] transition',
                  detailLevel === option.value ? 'border-indigo-500 bg-white text-indigo-700 shadow-sm' : 'border-slate-200 bg-white/70 text-slate-500 hover:border-indigo-200',
                )}
                onClick={() => setDetailLevel(option.value)}
                title={option.desc}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div data-testid="blueprint-advanced-panel" className="mt-3 rounded-2xl bg-slate-50 p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-xs font-semibold text-slate-500">고급 옵션</p>
          <p className="text-[11px] text-slate-400">
            {optionLabel(LENGTH_OPTIONS, lengthValue)} · {optionLabel(WRITING_STYLE_OPTIONS, writingStyleValue)} · {optionLabel(LANGUAGE_OPTIONS, languageValue)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button data-testid="blueprint-web-search" type="button" size="sm" variant={enableWebSearch ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setEnableWebSearch(!enableWebSearch)}><Search className="h-3.5 w-3.5" />웹 보강</Button>
          <Button data-testid="blueprint-web-research" type="button" size="sm" variant={enableWebResearch ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setEnableWebResearch(!enableWebResearch)}><Globe className="h-3.5 w-3.5" />웹 리서치</Button>
          <Button data-testid="blueprint-deep-comments" type="button" size="sm" variant={enableDeepComments ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setEnableDeepComments(!enableDeepComments)}><MessageSquare className="h-3.5 w-3.5" />댓글 심층 분석</Button>
          <Button data-testid="blueprint-agent-mode" type="button" size="sm" variant={enableAgentMode ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setEnableAgentMode(!enableAgentMode)}><Bot className="h-3.5 w-3.5" />에이전트</Button>
        </div>
      </div>
    </section>
  );
}

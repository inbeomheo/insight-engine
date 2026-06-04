'use client';

import type { KeyboardEvent } from 'react';
import { Bot, Combine, Cpu, Globe, Layers, MessageSquare, Search, SlidersHorizontal, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { STYLE_OPTIONS, LENGTH_OPTIONS, WRITING_STYLE_OPTIONS, LANGUAGE_OPTIONS } from '@/lib/constants';
import { useSettingsStore } from '@/stores/settingsStore';
import { cn } from '@/lib/utils';
import type { GenerationMode } from '@/lib/types';

const DETAIL_OPTIONS = [
  { value: 'brief', label: '간단', desc: '핵심만 빠르게' },
  { value: 'standard', label: '표준', desc: '균형 잡힌 결과' },
  { value: 'deep', label: '심층', desc: '맥락과 근거 강화' },
] as const;
type DetailLevel = (typeof DETAIL_OPTIONS)[number]['value'];

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

const MODE_OPTIONS: Array<{ id: GenerationMode; label: string; icon: typeof Sparkles }> = [
  { id: 'individual', label: '개별', icon: Sparkles },
  { id: 'combined', label: '통합', icon: Layers },
  { id: 'fusion', label: '퓨전', icon: Combine },
];

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
  const handleLengthKeyDown = (event: KeyboardEvent<HTMLSelectElement>) => {
    if (event.key === 'Home') {
      event.preventDefault();
      handleLengthChange('short');
    } else if (event.key === 'End') {
      event.preventDefault();
      handleLengthChange('long');
    }
  };
  const selectStyle = (styleId: string) => {
    setSelectedStyle(styleId);
    requestAnimationFrame(() => document.getElementById(`blueprint-style-${styleId}`)?.focus());
  };
  const handleStyleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? STYLE_OPTIONS.length - 1
          : (index + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + STYLE_OPTIONS.length) % STYLE_OPTIONS.length;
    selectStyle(STYLE_OPTIONS[nextIndex].id);
  };
  const selectMode = (mode: GenerationMode) => {
    if (mode !== 'individual' && multiSourceModeDisabled) return;
    setGenerationMode(mode);
    requestAnimationFrame(() => document.getElementById(`blueprint-mode-${mode}`)?.focus());
  };
  const handleModeKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const enabledModes = multiSourceModeDisabled ? MODE_OPTIONS.slice(0, 1) : MODE_OPTIONS;
    const currentIndex = Math.max(0, enabledModes.findIndex((option) => option.id === MODE_OPTIONS[index].id));
    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? enabledModes.length - 1
          : (currentIndex + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + enabledModes.length) % enabledModes.length;
    selectMode(enabledModes[nextIndex].id);
  };
  const selectDetail = (value: DetailLevel) => {
    setDetailLevel(value);
    requestAnimationFrame(() => document.getElementById(`blueprint-detail-${value}`)?.focus());
  };
  const handleDetailKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? DETAIL_OPTIONS.length - 1
          : (index + (['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1) + DETAIL_OPTIONS.length) % DETAIL_OPTIONS.length;
    selectDetail(DETAIL_OPTIONS[nextIndex].value);
  };

  return (
    <section
      data-testid="output-blueprint"
      role="region"
      aria-labelledby="output-blueprint-title"
      className="rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-5"
    >
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Output Blueprint</p>
          <h2 id="output-blueprint-title" className="mt-1 text-lg font-semibold text-slate-950">무엇으로 만들지 정하세요</h2>
        </div>
        <div data-testid="blueprint-model-summary" className="inline-flex max-w-full items-center gap-2 rounded-2xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
          <Cpu className="h-3.5 w-3.5 text-indigo-600" />
          <span className="truncate">모델 {modelLabel}</span>
        </div>
      </div>

      <div data-testid="blueprint-style-options" role="radiogroup" aria-label="산출물 스타일" className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {STYLE_OPTIONS.map((style, index) => (
          <button
            key={style.id}
            id={`blueprint-style-${style.id}`}
            type="button"
            data-testid={`blueprint-style-${style.id}`}
            role="radio"
            aria-checked={selectedStyle === style.id}
            tabIndex={selectedStyle === style.id ? 0 : -1}
            onClick={() => selectStyle(style.id)}
            onKeyDown={(event) => handleStyleKeyDown(event, index)}
            className={cn(
              'rounded-2xl border p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2',
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
          <div data-testid="blueprint-mode-options" role="radiogroup" aria-label="제작 모드" className="flex flex-wrap gap-2">
            {MODE_OPTIONS.map((option, index) => {
              const Icon = option.icon;
              const selected = visibleGenerationMode === option.id;
              const disabled = option.id !== 'individual' && multiSourceModeDisabled;
              return (
                <Button
                  key={option.id}
                  id={`blueprint-mode-${option.id}`}
                  data-testid={`blueprint-mode-${option.id}`}
                  role="radio"
                  aria-checked={selected}
                  aria-disabled={disabled}
                  aria-describedby={disabled && modeHint ? 'blueprint-mode-hint' : undefined}
                  disabled={disabled}
                  tabIndex={selected ? 0 : -1}
                  type="button"
                  size="sm"
                  variant={selected ? 'default' : 'outline'}
                  className="gap-1.5 rounded-full focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                  onClick={() => selectMode(option.id)}
                  onKeyDown={(event) => handleModeKeyDown(event, index)}
                >
                  <Icon className="h-3.5 w-3.5" />{option.label}
                </Button>
              );
            })}
          </div>
          {modeHint && (
            <p
              id="blueprint-mode-hint"
              data-testid="blueprint-mode-hint"
              role="status"
              aria-live="polite"
              className="mt-2 rounded-xl bg-indigo-50 px-3 py-2 text-[11px] leading-relaxed text-indigo-700"
            >
              {modeHint}
            </p>
          )}
        </div>

        <div data-testid="blueprint-modifier-controls" role="group" aria-label="길이 · 톤 · 언어" className="rounded-2xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-semibold text-slate-500">길이 · 톤 · 언어</p>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <select data-testid="blueprint-length-select" aria-label="길이" className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={lengthValue} onChange={(event) => handleLengthChange(event.currentTarget.value)} onKeyDown={handleLengthKeyDown}>{LENGTH_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
            <select data-testid="blueprint-tone-select" aria-label="톤" className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={writingStyleValue} onChange={(e) => setModifiers({ writing_style: e.target.value as typeof writingStyleValue })}>{WRITING_STYLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
            <select data-testid="blueprint-language-select" aria-label="언어" className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={languageValue} onChange={(e) => setModifiers({ language: e.target.value as 'ko' | 'en' | 'ja' })}>{LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
          </div>
        </div>

        <div data-testid="blueprint-detail-level" role="radiogroup" aria-label="상세도" className="rounded-2xl bg-slate-50 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-500"><SlidersHorizontal className="h-3.5 w-3.5" />상세도</p>
          <div className="grid grid-cols-3 gap-1.5">
            {DETAIL_OPTIONS.map((option, index) => (
              <button
                key={option.value}
                id={`blueprint-detail-${option.value}`}
                type="button"
                data-testid={`blueprint-detail-${option.value}`}
                role="radio"
                aria-checked={detailLevel === option.value}
                tabIndex={detailLevel === option.value ? 0 : -1}
                className={cn(
                  'rounded-xl border px-2 py-2 text-left text-[11px] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2',
                  detailLevel === option.value ? 'border-indigo-500 bg-white text-indigo-700 shadow-sm' : 'border-slate-200 bg-white/70 text-slate-500 hover:border-indigo-200',
                )}
                onClick={() => selectDetail(option.value)}
                onKeyDown={(event) => handleDetailKeyDown(event, index)}
                title={option.desc}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div data-testid="blueprint-advanced-panel" role="group" aria-label="고급 옵션" className="mt-3 rounded-2xl bg-slate-50 p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-xs font-semibold text-slate-500">고급 옵션</p>
          <p className="text-[11px] text-slate-400">
            {optionLabel(LENGTH_OPTIONS, lengthValue)} · {optionLabel(WRITING_STYLE_OPTIONS, writingStyleValue)} · {optionLabel(LANGUAGE_OPTIONS, languageValue)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button data-testid="blueprint-web-search" role="switch" aria-checked={enableWebSearch} type="button" size="sm" variant={enableWebSearch ? 'default' : 'outline'} className="gap-1.5 rounded-full focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2" onClick={() => setEnableWebSearch(!enableWebSearch)}><Search className="h-3.5 w-3.5" />웹 보강</Button>
          <Button data-testid="blueprint-web-research" role="switch" aria-checked={enableWebResearch} type="button" size="sm" variant={enableWebResearch ? 'default' : 'outline'} className="gap-1.5 rounded-full focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2" onClick={() => setEnableWebResearch(!enableWebResearch)}><Globe className="h-3.5 w-3.5" />웹 리서치</Button>
          <Button data-testid="blueprint-deep-comments" role="switch" aria-checked={enableDeepComments} type="button" size="sm" variant={enableDeepComments ? 'default' : 'outline'} className="gap-1.5 rounded-full focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2" onClick={() => setEnableDeepComments(!enableDeepComments)}><MessageSquare className="h-3.5 w-3.5" />댓글 심층 분석</Button>
          <Button data-testid="blueprint-agent-mode" role="switch" aria-checked={enableAgentMode} type="button" size="sm" variant={enableAgentMode ? 'default' : 'outline'} className="gap-1.5 rounded-full focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2" onClick={() => setEnableAgentMode(!enableAgentMode)}><Bot className="h-3.5 w-3.5" />에이전트</Button>
        </div>
      </div>
    </section>
  );
}

'use client';

import { Bot, Combine, Layers, Search, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { STYLE_OPTIONS, LENGTH_OPTIONS, WRITING_STYLE_OPTIONS, LANGUAGE_OPTIONS } from '@/lib/constants';
import { useSettingsStore } from '@/stores/settingsStore';
import { cn } from '@/lib/utils';

export default function OutputBlueprint() {
  const selectedStyle = useSettingsStore((s) => s.selectedStyle);
  const setSelectedStyle = useSettingsStore((s) => s.setSelectedStyle);
  const generationMode = useSettingsStore((s) => s.generationMode);
  const setGenerationMode = useSettingsStore((s) => s.setGenerationMode);
  const modifiers = useSettingsStore((s) => s.modifiers);
  const setModifiers = useSettingsStore((s) => s.setModifiers);
  const enableWebSearch = useSettingsStore((s) => s.enableWebSearch);
  const setEnableWebSearch = useSettingsStore((s) => s.setEnableWebSearch);
  const enableAgentMode = useSettingsStore((s) => s.enableAgentMode);
  const setEnableAgentMode = useSettingsStore((s) => s.setEnableAgentMode);

  return (
    <section className="rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Output Blueprint</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-950">무엇으로 만들지 정하세요</h2>
      </div>
      <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
        {STYLE_OPTIONS.map((style) => (
          <button key={style.id} type="button" onClick={() => setSelectedStyle(style.id)} className={cn('rounded-2xl border p-3 text-left transition', selectedStyle === style.id ? 'border-indigo-500 bg-indigo-50 text-indigo-950 shadow-sm' : 'border-slate-200 bg-slate-50/60 hover:border-indigo-200 hover:bg-white')}>
            <span className="text-lg">{style.emoji}</span><p className="mt-1 text-sm font-semibold">{style.label}</p>
          </button>
        ))}
      </div>
      <div className="mt-5 grid gap-3 lg:grid-cols-3">
        <div className="rounded-2xl bg-slate-50 p-3"><p className="mb-2 text-xs font-semibold text-slate-500">제작 모드</p><div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant={generationMode === 'individual' ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setGenerationMode('individual')}><Sparkles className="h-3.5 w-3.5" />개별</Button>
          <Button type="button" size="sm" variant={generationMode === 'combined' ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setGenerationMode('combined')}><Layers className="h-3.5 w-3.5" />통합</Button>
          <Button type="button" size="sm" variant={generationMode === 'fusion' ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setGenerationMode('fusion')}><Combine className="h-3.5 w-3.5" />퓨전</Button>
        </div></div>
        <div className="rounded-2xl bg-slate-50 p-3"><p className="mb-2 text-xs font-semibold text-slate-500">길이 · 톤 · 언어</p><div className="grid grid-cols-3 gap-2 text-xs">
          <select className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={modifiers.length} onChange={(e) => setModifiers({ length: e.target.value as 'short' | 'medium' | 'long' })}>{LENGTH_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
          <select className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={modifiers.writing_style} onChange={(e) => setModifiers({ writing_style: e.target.value as typeof modifiers.writing_style })}>{WRITING_STYLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
          <select className="rounded-lg border border-slate-200 bg-white px-2 py-2" value={modifiers.language} onChange={(e) => setModifiers({ language: e.target.value as 'ko' | 'en' | 'ja' })}>{LANGUAGE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        </div></div>
        <div className="rounded-2xl bg-slate-50 p-3"><p className="mb-2 text-xs font-semibold text-slate-500">고급 옵션</p><div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant={enableWebSearch ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setEnableWebSearch(!enableWebSearch)}><Search className="h-3.5 w-3.5" />웹 보강</Button>
          <Button type="button" size="sm" variant={enableAgentMode ? 'default' : 'outline'} className="gap-1.5 rounded-full" onClick={() => setEnableAgentMode(!enableAgentMode)}><Bot className="h-3.5 w-3.5" />에이전트</Button>
        </div></div>
      </div>
    </section>
  );
}

# Studio Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insight Engine을 입력폼 중심 앱에서 소스→설정→생성→후처리→예약/내보내기까지 이어지는 AI 콘텐츠 스튜디오로 재구성한다.

**Architecture:** 기존 Flask API와 Zustand store는 유지하고, Next.js 프론트 정보구조를 `studio` 컴포넌트 계층으로 재배치한다. 기존 `UrlInput`, `TextInput`, `ResultCard`, `ScheduleModal`, `NotebookLmSection`을 재사용하되 shell/layout/blueprint/right-panel을 새로 만든다.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS, Zustand, shadcn/ui, Flask API, Playwright QA.

---

## File Map

- Create: `frontend/components/studio/studioConfig.ts` — Studio 단계, 빠른 액션, 생성 CTA 문구.
- Create: `frontend/components/studio/StudioShell.tsx` — 좌측/중앙/우측 3분할 shell.
- Create: `frontend/components/studio/StudioHero.tsx` — 제품 컨셉과 작업 단계 요약.
- Create: `frontend/components/studio/SourceComposer.tsx` — URL/텍스트 입력 통합 카드.
- Create: `frontend/components/studio/OutputBlueprint.tsx` — 산출물/모드/톤/언어/고급 옵션.
- Create: `frontend/components/studio/GenerateDock.tsx` — 현재 소스와 모드에 맞는 주 생성 버튼.
- Create: `frontend/components/studio/StudioRightPanel.tsx` — 작업 요약, 최근 결과, 빠른 액션.
- Modify: `frontend/app/page.tsx` — 기존 main을 studio 구조로 교체.
- Modify: `frontend/app/globals.css` — studio 배경/표면 토큰 보강.
- Modify: `frontend/components/layout/Header.tsx` — Studio header 톤.
- Modify: `frontend/components/layout/Sidebar.tsx` — 작업 히스토리 rail 톤.
- Modify: `frontend/components/result/ResultCard.tsx` — Workbench 카드 톤.
- Modify: `frontend/components/result/NotebookLmSection.tsx` — NLM 산출물 패널 톤.
- Modify: `tests/e2e/autoqa/run_autoqa.py` — studio layout 확인 case 추가.

---

## Task 1: Studio config 추가

**Files:**
- Create: `frontend/components/studio/studioConfig.ts`

- [ ] **Step 1: 파일 생성**

```ts
import { CalendarDays, Download, FileText, Sparkles, Wand2 } from 'lucide-react';

export const STUDIO_STEPS = [
  { id: 'source', label: '소스 입력', description: 'URL, 텍스트, 파일, 음성을 준비합니다.' },
  { id: 'blueprint', label: '산출물 설계', description: '스타일, 톤, 길이, 제작 모드를 고릅니다.' },
  { id: 'generate', label: 'AI 생성', description: '선택 모델로 콘텐츠를 생성합니다.' },
  { id: 'workbench', label: '후처리', description: 'NLM, 변환, 내보내기, 예약을 처리합니다.' },
] as const;

export const QUICK_ACTIONS = [
  { id: 'export', label: '내보내기', icon: Download },
  { id: 'schedule', label: '예약', icon: CalendarDays },
  { id: 'nlm', label: 'NLM 산출물', icon: Sparkles },
  { id: 'rewrite', label: '플랫폼 변환', icon: Wand2 },
  { id: 'prompt', label: '프롬프트', icon: FileText },
] as const;

export function getGenerateLabel(sourceCount: number, mode: string): string {
  if (sourceCount <= 0) return '소스를 추가하면 생성할 수 있습니다';
  if (mode === 'combined') return `${sourceCount}개 소스 통합 콘텐츠 생성`;
  if (mode === 'fusion') return `${sourceCount}개 소스 퓨전 분석 시작`;
  if (sourceCount === 1) return '1개 소스로 콘텐츠 생성';
  return `${sourceCount}개 소스 각각 생성`;
}
```

- [ ] **Step 2: 타입 확인**

Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Expected: PASS.

- [ ] **Step 3: 커밋**

Run: `git add frontend/components/studio/studioConfig.ts; git commit -m "feat: add studio configuration"`

---

## Task 2: Studio shell 추가

**Files:**
- Create: `frontend/components/studio/StudioShell.tsx`

- [ ] **Step 1: 파일 생성**

```tsx
'use client';

import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface StudioShellProps {
  sidebar: ReactNode;
  header: ReactNode;
  main: ReactNode;
  rightPanel: ReactNode;
  className?: string;
}

export default function StudioShell({ sidebar, header, main, rightPanel, className }: StudioShellProps) {
  return (
    <div className={cn('min-h-screen bg-[radial-gradient(circle_at_top_left,#eef2ff_0,#f6f7fb_34%,#f8fafc_100%)] text-foreground', className)}>
      <div className="flex h-screen overflow-hidden">
        {sidebar}
        <div className="flex min-w-0 flex-1 flex-col">
          {header}
          <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px]">
            <main id="main-content" className="min-w-0 overflow-y-auto px-4 py-5 sm:px-6 lg:px-8" role="main">
              <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">{main}</div>
            </main>
            <aside className="hidden min-h-0 border-l border-slate-200/70 bg-white/70 backdrop-blur-xl xl:block">{rightPanel}</aside>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 검증/커밋**

Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/studio/StudioShell.tsx; git commit -m "feat: add studio shell layout"`

---

## Task 3: Studio hero 추가

**Files:**
- Create: `frontend/components/studio/StudioHero.tsx`

- [ ] **Step 1: 파일 생성**

```tsx
'use client';

import { Badge } from '@/components/ui/badge';
import { STUDIO_STEPS } from './studioConfig';

interface StudioHeroProps {
  modelLabel: string;
  resultCount: number;
}

export default function StudioHero({ modelLabel, resultCount }: StudioHeroProps) {
  return (
    <section className="overflow-hidden rounded-[28px] border border-white/70 bg-white/85 p-5 shadow-sm shadow-slate-200/70 backdrop-blur-xl sm:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <Badge className="w-fit rounded-full bg-indigo-50 px-3 py-1 text-indigo-700 hover:bg-indigo-50">AI Content Studio</Badge>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">소스에서 발행까지 한 번에</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">YouTube, 웹, 텍스트를 넣고 Blog+SEO, 요약, NLM 산출물, 예약 발행까지 하나의 작업실에서 처리합니다.</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 lg:w-[520px]">
          {STUDIO_STEPS.map((step, index) => (
            <div key={step.id} className="rounded-2xl border border-slate-200/70 bg-slate-50/80 p-3">
              <div className="mb-2 flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-[11px] font-bold text-white">{index + 1}</div>
              <p className="font-semibold text-slate-900">{step.label}</p>
              <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-slate-500">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-slate-100 px-3 py-1">모델: {modelLabel || '자동 선택'}</span>
        <span className="rounded-full bg-slate-100 px-3 py-1">생성 결과: {resultCount}개</span>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: 검증/커밋**

Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/studio/StudioHero.tsx; git commit -m "feat: add studio hero"`

---

## Task 4: Source Composer 추가

**Files:**
- Create: `frontend/components/studio/SourceComposer.tsx`

- [ ] **Step 1: 파일 생성**

```tsx
'use client';

import { useState } from 'react';
import { FileText, Link2 } from 'lucide-react';
import UrlInput from '@/components/input/UrlInput';
import TextInput from '@/components/input/TextInput';
import { cn } from '@/lib/utils';

interface SourceComposerProps {
  urls: string[];
  isLoading: boolean;
  onAddUrl: (url: string) => void;
  onAddUrls: (urls: string[]) => void;
  onRemoveUrl: (url: string) => void;
  onToggleSettings: () => void;
  onGenerateUrl: () => void;
  onGenerateText: (text: string) => Promise<boolean>;
}

export default function SourceComposer(props: SourceComposerProps) {
  const [tab, setTab] = useState<'url' | 'text'>('url');

  return (
    <section className="rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Source Composer</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">분석할 소스를 준비하세요</h2>
        </div>
        <div className="flex rounded-full bg-slate-100 p-1 text-xs font-medium">
          <button type="button" onClick={() => setTab('url')} className={cn('flex items-center gap-1.5 rounded-full px-3 py-1.5', tab === 'url' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500')}><Link2 className="h-3.5 w-3.5" /> URL</button>
          <button type="button" onClick={() => setTab('text')} className={cn('flex items-center gap-1.5 rounded-full px-3 py-1.5', tab === 'text' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500')}><FileText className="h-3.5 w-3.5" /> 텍스트</button>
        </div>
      </div>
      {tab === 'url' ? (
        <UrlInput urls={props.urls} onAddUrl={props.onAddUrl} onAddUrls={props.onAddUrls} onRemoveUrl={props.onRemoveUrl} onToggleSettings={props.onToggleSettings} isLoading={props.isLoading} onGenerate={props.onGenerateUrl} />
      ) : (
        <TextInput onGenerate={props.onGenerateText} isLoading={props.isLoading} />
      )}
    </section>
  );
}
```

- [ ] **Step 2: 검증/커밋**

Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/studio/SourceComposer.tsx; git commit -m "feat: add source composer"`

---

## Task 5: Output Blueprint 추가

**Files:**
- Create: `frontend/components/studio/OutputBlueprint.tsx`

- [ ] **Step 1: 파일 생성**

```tsx
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
```

- [ ] **Step 2: 검증/커밋**

Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/studio/OutputBlueprint.tsx; git commit -m "feat: add output blueprint"`

---

## Task 6: Generate Dock 추가

**Files:**
- Create: `frontend/components/studio/GenerateDock.tsx`

- [ ] **Step 1: 파일 생성**

```tsx
'use client';

import { Combine, Layers, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getGenerateLabel } from './studioConfig';

interface GenerateDockProps {
  sourceCount: number;
  mode: string;
  isLoading: boolean;
  onGenerate: () => void;
  onGenerateMerged: () => void;
  onGenerateFusion: () => void;
}

export default function GenerateDock({ sourceCount, mode, isLoading, onGenerate, onGenerateMerged, onGenerateFusion }: GenerateDockProps) {
  const disabled = sourceCount <= 0 || isLoading;
  const Icon = mode === 'fusion' ? Combine : mode === 'combined' ? Layers : Sparkles;
  const handler = mode === 'fusion' ? onGenerateFusion : mode === 'combined' ? onGenerateMerged : onGenerate;
  return (
    <section className="sticky bottom-4 z-20 rounded-[24px] border border-indigo-100 bg-white/90 p-3 shadow-lg shadow-indigo-100/70 backdrop-blur-xl">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div><p className="text-xs font-semibold text-indigo-700">Ready to Generate</p><p className="text-sm text-slate-500">소스 {sourceCount}개 · 모드 {mode}</p></div>
        <Button disabled={disabled} onClick={handler} className="h-12 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 text-sm font-semibold shadow-md shadow-indigo-200 hover:opacity-95">
          {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Icon className="mr-2 h-4 w-4" />}{getGenerateLabel(sourceCount, mode)}
        </Button>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: 검증/커밋**

Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/studio/GenerateDock.tsx; git commit -m "feat: add studio generate dock"`

---

## Task 7: Right Panel 추가

**Files:**
- Create: `frontend/components/studio/StudioRightPanel.tsx`

- [ ] **Step 1: 파일 생성**

```tsx
'use client';

import { CalendarDays, FileText, Sparkles } from 'lucide-react';
import { QUICK_ACTIONS } from './studioConfig';
import type { Report } from '@/lib/types';

interface StudioRightPanelProps {
  reports: Report[];
  sourceCount: number;
  schedulesCount: number;
}

export default function StudioRightPanel({ reports, sourceCount, schedulesCount }: StudioRightPanelProps) {
  const nlmCount = reports.reduce((sum, report) => sum + (report.notebooklm?.artifacts?.length ?? 0), 0);
  const latest = reports.slice(0, 4);
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Workspace</p><h2 className="mt-1 text-lg font-semibold text-slate-950">작업 요약</h2><div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs"><div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{sourceCount}</p><p className="text-slate-500">소스</p></div><div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{reports.length}</p><p className="text-slate-500">결과</p></div><div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{nlmCount}</p><p className="text-slate-500">NLM</p></div></div></section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> 빠른 액션</div><div className="mt-3 grid grid-cols-2 gap-2">{QUICK_ACTIONS.map((action) => <div key={action.id} className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-600"><action.icon className="mb-2 h-4 w-4 text-indigo-600" />{action.label}</div>)}</div></section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><FileText className="h-4 w-4 text-indigo-600" /> 최근 결과</div><div className="mt-3 space-y-2">{latest.length === 0 ? <p className="text-xs text-slate-500">아직 생성된 결과가 없습니다.</p> : latest.map((report) => <div key={report.id} className="rounded-2xl bg-slate-50 p-3"><p className="line-clamp-2 text-xs font-medium text-slate-800">{report.title}</p><p className="mt-1 text-[11px] text-slate-500">{report.style}</p></div>)}</div></section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><CalendarDays className="h-4 w-4 text-indigo-600" /> 예약</div><p className="mt-2 text-xs text-slate-500">예약된 발행 {schedulesCount}개</p></section>
    </div>
  );
}
```

- [ ] **Step 2: 검증/커밋**

Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/studio/StudioRightPanel.tsx; git commit -m "feat: add studio right panel"`

---

## Task 8: page.tsx에 Studio 구조 적용

**Files:**
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: imports 추가**

```tsx
import StudioShell from '@/components/studio/StudioShell';
import StudioHero from '@/components/studio/StudioHero';
import SourceComposer from '@/components/studio/SourceComposer';
import OutputBlueprint from '@/components/studio/OutputBlueprint';
import GenerateDock from '@/components/studio/GenerateDock';
import StudioRightPanel from '@/components/studio/StudioRightPanel';
```

- [ ] **Step 2: 모델 라벨 추가**

```tsx
const selectedProvider = useSettingsStore((s) => s.selectedProvider);
const selectedModel = useSettingsStore((s) => s.selectedModel);
const modelLabel = selectedModel || selectedProvider || '자동 선택';
```

- [ ] **Step 3: 기존 main 영역을 Studio 컴포넌트 조합으로 교체**

Use `StudioShell` as outer layout, keep all modal components after it in a fragment. Preserve handlers: `handleGenerate`, `handleGenerateMerged`, `handleGenerateFusion`, `handleScheduleOpen`, `handleScheduleSubmit`.

Essential JSX shape:

```tsx
<StudioShell
  sidebar={<Sidebar />}
  header={<Header />}
  rightPanel={<StudioRightPanel reports={reports} sourceCount={urls.length} schedulesCount={schedules.length} />}
  main={<><StudioHero modelLabel={modelLabel} resultCount={reports.length} /><SourceComposer ... /><OutputBlueprint />{/* toolbar, results, GenerateDock */}</>}
/>
```

- [ ] **Step 4: 검증/커밋**

Run: `npm run lint --prefix frontend`
Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/app/page.tsx; git commit -m "feat: apply studio home layout"`

---

## Task 9: Header/Sidebar Studio 톤 정리

**Files:**
- Modify: `frontend/components/layout/Header.tsx`
- Modify: `frontend/components/layout/Sidebar.tsx`

- [ ] **Step 1: Header 변경**

Change brand label to `Insight Studio` and header class to:

```tsx
<header className="h-16 border-b border-white/70 flex items-center justify-between px-4 shrink-0 bg-white/75 backdrop-blur-xl" role="banner">
```

- [ ] **Step 2: Sidebar 변경**

Change aside base class to:

```tsx
'w-[280px] border-r border-white/70 bg-white/75 backdrop-blur-xl dark:bg-zinc-900 flex flex-col h-full shrink-0 z-50'
```

- [ ] **Step 3: 검증/커밋**

Run: `npm run lint --prefix frontend`
Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/layout/Header.tsx frontend/components/layout/Sidebar.tsx; git commit -m "style: refresh studio navigation"`

---

## Task 10: 전역 Studio visual polish

**Files:**
- Modify: `frontend/app/globals.css`

- [ ] **Step 1: root 색상 조정**

```css
--background: #F6F7FB;
--foreground: #0F172A;
--muted: #F1F5F9;
--muted-foreground: #64748B;
--border: #E2E8F0;
--input: #CBD5E1;
```

- [ ] **Step 2: utility 추가**

```css
.studio-card { @apply rounded-[24px] border border-slate-200/80 bg-white shadow-sm shadow-slate-200/60; }
.studio-panel { @apply rounded-[28px] border border-white/70 bg-white/80 shadow-sm shadow-slate-200/70 backdrop-blur-xl; }
```

- [ ] **Step 3: 검증/커밋**

Run: `npm run lint --prefix frontend`
Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/app/globals.css; git commit -m "style: add studio visual system"`

---

## Task 11: Result Workbench/NLM 개선

**Files:**
- Modify: `frontend/components/result/ResultCard.tsx`
- Modify: `frontend/components/result/NotebookLmSection.tsx`

- [ ] **Step 1: ResultCard 카드 class에 workbench 톤 적용**

Add rounded 24px, slate border, white surface, subtle shadow to the main Card.

- [ ] **Step 2: Action area에 Workbench label 추가**

```tsx
<span className="mr-2 hidden text-xs font-medium text-slate-400 sm:inline">Workbench</span>
```

- [ ] **Step 3: NotebookLmSection wrapper 개선**

```tsx
<div className="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-3">
  <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-indigo-700">NotebookLM Artifacts</p>
```

- [ ] **Step 4: 검증/커밋**

Run: `npm run lint --prefix frontend`
Run: `cd frontend; .\node_modules\.bin\tsc.cmd --noEmit`
Run: `git add frontend/components/result/ResultCard.tsx frontend/components/result/NotebookLmSection.tsx; git commit -m "style: refresh result workbench"`

---

## Task 12: Auto QA selector 보강

**Files:**
- Modify: `tests/e2e/autoqa/run_autoqa.py`

- [ ] **Step 1: matrix row 추가**

```python
("studio-layout", "스튜디오 레이아웃", "studio shell and composer visible"),
```

- [ ] **Step 2: home-load 뒤 case 추가**

```python
try:
    studio_visible = page.get_by_text("AI Content Studio").count() > 0 or page.get_by_text("Source Composer").count() > 0
    report.record("studio-layout", studio_visible, "studio hero/source composer visible" if studio_visible else screenshot(page, "studio-layout-fail.png"))
except Exception as exc:
    report.record("studio-layout", False, repr(exc))
```

- [ ] **Step 3: 검증/커밋**

Run: `python -m py_compile tests\e2e\autoqa\run_autoqa.py`
Run: `git add tests/e2e/autoqa/run_autoqa.py; git commit -m "test: cover studio layout"`

---

## Task 13: 전체 QA 및 최종 푸시

**Files:**
- Modify: `QA_REPORT.md`
- Maybe modify: `tests/e2e/autoqa/artifacts/*.png`

- [ ] **Step 1: 전체 자동 QA 실행**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests\e2e\autoqa\run_stack_autoqa.ps1
```

Expected: `Failures: 0` in `QA_REPORT.md`.

- [ ] **Step 2: 브라우저 스모크**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(headless=True); page=b.new_page(viewport={'width':1440,'height':1000}); page.goto('http://127.0.0.1:3000', wait_until='networkidle', timeout=60000); assert page.get_by_text('AI Content Studio').count() > 0; page.screenshot(path='tests/e2e/autoqa/artifacts/studio-home.png', full_page=True); b.close(); p.stop()"
```

Expected: no assertion error and `studio-home.png` created.

- [ ] **Step 3: 커밋/푸시**

Run:

```powershell
git add QA_REPORT.md tests/e2e/autoqa/artifacts/studio-home.png
git commit -m "test: verify studio redesign"
git push
```

---

## Self Review

- Spec coverage: Visual shell, source composer, output blueprint, generate CTA, result workbench, NLM, QA가 모두 task에 포함됨.
- Backend scope: Flask API 대규모 변경은 제외되어 spec 비범위와 일치함.
- Risk: `TextInput`/`UrlInput` 기존 내부 버튼이 SourceComposer 카드 안에서 중복 CTA처럼 보일 수 있음. Task 8 이후 브라우저 확인에서 중복이 크면 입력 컴포넌트 내부 버튼을 optional prop으로 숨기는 보정 task를 추가한다.
- Completion evidence: lint, tsc, auto QA, Playwright screenshot, 커밋/푸시가 필요함.

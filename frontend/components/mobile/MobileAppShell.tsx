'use client';

import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import dynamic from 'next/dynamic';
import {
  ArrowLeft,
  ArrowUp,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ExternalLink,
  Grid2X2,
  Loader2,
  MessageSquare,
  PlusCircle,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import TextInput from '@/components/input/TextInput';
import { STYLE_OPTIONS } from '@/lib/constants';
import { buildLocalDashboardStats } from '@/lib/dashboard-summary';
import { cn } from '@/lib/utils';
import { getStyleLabel } from '@/lib/helpers';
import { createKnowledgeNote, isApiError, type NoteDuplicateWarning } from '@/lib/api';
import { MAX_LOCAL_REPORTS, useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import type { GenerationMode, Report } from '@/lib/types';

// 영상 채팅 패널 — 특정 동작에서만 열리므로 dynamic import (ResultCard와 동일 패턴)
const VideoChatPanel = dynamic(() => import('@/components/chat/VideoChatPanel'), { ssr: false });

type MobileTab = 'create' | 'library' | 'dashboard';
type SourceInputTab = 'url' | 'text';

function noteSourceTypeFromUrl(url: string): 'youtube' | 'article' {
  return /(?:youtube\.com|youtu\.be)/i.test(url) ? 'youtube' : 'article';
}

interface MobileAppShellProps {
  reports: Report[];
  urls: string[];
  isLoading: boolean;
  error: string | null;
  onAddUrl: (url: string) => string | null;
  onRemoveUrl: (url: string) => void;
  onGenerate: (draftUrl?: string) => void;
  inputTab: SourceInputTab;
  onInputTabChange: (tab: SourceInputTab) => void;
  textValue: string;
  onTextChange: (text: string) => void;
  onGenerateText: (text: string) => void;
}

const TAB_META: Record<MobileTab, { label: string; icon: typeof PlusCircle }> = {
  create: { label: '생성', icon: PlusCircle },
  library: { label: '라이브러리', icon: Grid2X2 },
  dashboard: { label: '대시보드', icon: BarChart3 },
};

const CATEGORY_DOTS = ['bg-[#E90043]', 'bg-[#7C5CFF]', 'bg-[#20C997]', 'bg-[#2F80ED]', 'bg-[#E90043]', 'bg-[#F2B705]'];
const MODE_LABELS: Record<GenerationMode, string> = {
  individual: '개별',
  combined: '통합',
  fusion: '퓨전',
};

function MobileBottomNav({ activeTab, onChange }: { activeTab: MobileTab; onChange: (tab: MobileTab) => void }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-border/60 bg-background/95 px-7 pb-[calc(env(safe-area-inset-bottom)+0.55rem)] pt-2 backdrop-blur" aria-label="모바일 하단 네비게이션">
      <div className="mx-auto grid max-w-[430px] grid-cols-3 gap-2">
        {(Object.keys(TAB_META) as MobileTab[]).map((tab) => {
          const Icon = TAB_META[tab].icon;
          const active = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              className={cn(
                'signal-meta flex flex-col items-center justify-center gap-1 rounded-sm py-1.5 text-[10px] font-semibold transition-colors',
                active ? 'text-primary' : 'text-muted-foreground/55'
              )}
              onClick={() => onChange(tab)}
            >
              <Icon className={cn('h-5 w-5', active && 'stroke-[2.4]')} />
              <span>{TAB_META[tab].label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

function MobileCreateView({
  urls,
  isLoading,
  error,
  onAddUrl,
  onRemoveUrl,
  onGenerate,
  inputTab,
  onInputTabChange,
  textValue,
  onTextChange,
  onGenerateText,
}: Pick<MobileAppShellProps, 'urls' | 'isLoading' | 'error' | 'onAddUrl' | 'onRemoveUrl' | 'onGenerate' | 'inputTab' | 'onInputTabChange' | 'textValue' | 'onTextChange' | 'onGenerateText'>) {
  const [draftUrl, setDraftUrl] = useState('');
  const selectedStyle = useSettingsStore((s) => s.selectedStyle);
  const setSelectedStyle = useSettingsStore((s) => s.setSelectedStyle);
  const generationMode = useSettingsStore((s) => s.generationMode);
  const setGenerationMode = useSettingsStore((s) => s.setGenerationMode);
  const [inputError, setInputError] = useState('');

  const submitDraft = () => {
    const value = draftUrl.trim();
    if (!value) return;
    const err = onAddUrl(value);
    if (err) {
      setInputError(err);
      return;
    }
    setInputError('');
    setDraftUrl('');
  };

  const handleGenerateClick = () => {
    const value = draftUrl.trim();
    if (value && urls.length === 0) {
      onGenerate(value);
      setDraftUrl('');
      setInputError('');
      return;
    }
    if (value) {
      onGenerate(value);
      setDraftUrl('');
      setInputError('');
      return;
    }
    onGenerate();
  };

  const handleStyleSelect = (styleId: string) => {
    setSelectedStyle(selectedStyle === styleId && styleId !== 'summary' ? 'summary' : styleId);
  };

  return (
    <section className="min-h-dvh px-6 pb-28 pt-12">
      <div className="mb-7 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-sm bg-foreground">
            <span className="h-2.5 w-2.5 rounded-full bg-primary" />
          </span>
          <span className="text-[15px] font-bold tracking-tight">Insight Engine</span>
        </div>
        <span className="signal-meta text-[10px] text-muted-foreground/55">모바일</span>
      </div>

      <p className="signal-meta mb-2 text-[10px] font-bold text-primary">새 분석 · STEP 01</p>
      <h1 className="mb-5 text-[32px] font-black leading-[1.05] tracking-[-0.04em] text-foreground">
        어떤 자료를<br />콘텐츠로?
      </h1>

      <div className="mb-3 flex gap-1" role="group" aria-label="입력 방식 선택">
        {(['url', 'text'] as SourceInputTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            aria-pressed={inputTab === tab}
            className={cn(
              'signal-meta rounded-sm px-3 py-1.5 text-[11px] font-bold transition-colors',
              inputTab === tab ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground'
            )}
            onClick={() => onInputTabChange(tab)}
          >
            {tab === 'url' ? 'URL 입력' : '텍스트 붙여넣기'}
          </button>
        ))}
      </div>

      {inputTab === 'url' ? (
        <>
          <div className="mb-2 flex min-h-[58px] items-center gap-2 border-[1.5px] border-foreground bg-card px-3 shadow-[3px_3px_0_var(--foreground)]">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#E90043]" />
            <input
              className="min-w-0 flex-1 bg-transparent text-sm font-medium outline-none placeholder:text-muted-foreground/45"
              value={draftUrl}
              type="url"
              inputMode="url"
              placeholder="URL 붙여넣기"
              onChange={(e) => setDraftUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  submitDraft();
                }
              }}
            />
            <button
              type="button"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm bg-primary text-primary-foreground shadow-[2px_2px_0_var(--foreground)] active:translate-x-[1px] active:translate-y-[1px] active:shadow-none"
              onClick={submitDraft}
              aria-label="URL 추가"
            >
              <ArrowUp className="h-5 w-5" />
            </button>
          </div>
          <div className="signal-meta mb-3 flex gap-2 text-[10px] text-muted-foreground/50">
            <span>YouTube</span><span>·</span><span>웹</span><span>·</span><span>RSS</span><span>·</span><span>arXiv</span><span>·</span><span>Podcast</span>
          </div>
        </>
      ) : (
        <div className="mb-3">
          <TextInput
            value={textValue}
            onChange={onTextChange}
            onGenerate={onGenerateText}
            isLoading={isLoading}
          />
        </div>
      )}
      {(inputError || error) && (
        <p className="mb-3 rounded-sm border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">{inputError || error}</p>
      )}

      {inputTab === 'url' && urls.length > 0 && (
        <div className="mb-5 space-y-2">
          {urls.map((url) => (
            <div key={url} className="flex h-12 items-center gap-2 border border-border/60 bg-card px-3 text-xs text-muted-foreground">
              <span className="h-2 w-2 shrink-0 rounded-full bg-[#E90043]" />
              <span className="min-w-0 flex-1 truncate font-medium text-foreground/75">{url}</span>
              <span className="signal-meta text-[9px] text-muted-foreground/45">YouTube</span>
              <button type="button" onClick={() => onRemoveUrl(url)} aria-label="URL 제거">
                <X className="h-4 w-4 text-muted-foreground/45" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold">출력 스타일 <span className="text-muted-foreground/45">{STYLE_OPTIONS.length}</span></h2>
          <span className="signal-meta text-[10px] font-semibold text-primary">선택 1 · 다시 누르면 기본값</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {STYLE_OPTIONS.map((style) => {
            const active = selectedStyle === style.id;
            return (
              <button
                key={style.id}
                type="button"
                aria-pressed={active}
                aria-label={`${style.label} 스타일 선택${style.description ? `: ${style.description}` : ''}`}
                title={active && style.id !== 'summary' ? '다시 누르면 요약 기본값으로 돌아가요' : style.description}
                className={cn(
                  'rounded-full border px-4 py-2 text-xs font-bold transition-colors',
                  active
                    ? 'border-foreground bg-foreground text-background'
                    : 'border-border/70 bg-card text-foreground/75 shadow-[0_1px_0_rgba(21,23,31,0.04)]'
                )}
                onClick={() => handleStyleSelect(style.id)}
              >
                {style.label}
              </button>
            );
          })}
        </div>
      </div>

      {inputTab === 'url' && (
        <>
          <div className="mb-7">
            <h2 className="mb-3 text-sm font-bold">생성 모드</h2>
            <div className="grid grid-cols-3 bg-muted p-1">
              {(['individual', 'combined', 'fusion'] as GenerationMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  className={cn(
                    'h-11 text-sm font-bold transition-colors',
                    generationMode === mode ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground/55'
                  )}
                  onClick={() => setGenerationMode(mode)}
                >
                  {MODE_LABELS[mode]}
                </button>
              ))}
            </div>
          </div>

          <Button
            className="h-14 w-full rounded-sm bg-primary text-base font-black text-primary-foreground shadow-[0_8px_18px_rgba(47,84,235,0.22)] hover:bg-primary/95"
            disabled={isLoading || (urls.length === 0 && !draftUrl.trim())}
            onClick={handleGenerateClick}
          >
            {isLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : null}
            콘텐츠 생성 <span className="ml-1 text-xs opacity-80">×{Math.max(1, urls.length || (draftUrl.trim() ? 1 : 0))}</span>
          </Button>
        </>
      )}
    </section>
  );
}

function MobileLibraryView({ reports, onOpen }: { reports: Report[]; onOpen: (report: Report) => void }) {
  const counts = useMemo(() => {
    const byStyle = new Map<string, number>();
    reports.forEach((report) => byStyle.set(report.style, (byStyle.get(report.style) || 0) + 1));
    return byStyle;
  }, [reports]);

  return (
    <section className="min-h-dvh px-6 pb-28 pt-12">
      <div className="mb-5 flex items-end justify-between">
        <h1 className="text-[28px] font-black tracking-[-0.035em]">라이브러리</h1>
        <span className="signal-meta text-[10px] text-muted-foreground/45">{reports.length}개</span>
      </div>
      <div className="mb-5 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none]">
        <span className="shrink-0 rounded-full bg-foreground px-4 py-2 text-xs font-bold text-background">전체 {reports.length}</span>
        {STYLE_OPTIONS.slice(0, 5).map((style) => (
          <span key={style.id} className="shrink-0 rounded-full border border-border/70 bg-card px-4 py-2 text-xs font-semibold text-muted-foreground">
            {style.label} {counts.get(style.id) || 0}
          </span>
        ))}
      </div>

      <div className="space-y-3">
        {reports.length === 0 ? (
          <div className="border border-dashed border-border/70 bg-card/60 px-5 py-10 text-center">
            <p className="text-sm font-bold text-foreground/80">아직 생성된 콘텐츠가 없어</p>
            <p className="mt-1 text-xs text-muted-foreground">생성 탭에서 첫 분석을 만들어봐.</p>
          </div>
        ) : (
          reports.map((report, index) => (
            <button
              key={report.id}
              type="button"
              className="block w-full border border-border/70 bg-card px-4 py-4 text-left shadow-[0_1px_8px_rgba(21,23,31,0.04)] transition-transform active:scale-[0.99]"
              onClick={() => onOpen(report)}
            >
              <div className="mb-2 flex items-center gap-2">
                <span className={cn('h-2.5 w-2.5 rounded-full', CATEGORY_DOTS[index % CATEGORY_DOTS.length])} />
                <span className="signal-meta text-[9px] text-muted-foreground/55">{getStyleLabel(report.style)}</span>
              </div>
              <h2 className="line-clamp-2 text-[15px] font-black leading-snug tracking-[-0.02em]">{report.title}</h2>
              <p className="signal-meta mt-3 text-[9px] text-muted-foreground/45">
                {report.time} · {Math.round((report.usage?.total_tokens || 0) / 100) / 10 || 0}k tokens · 초안
              </p>
            </button>
          ))
        )}
      </div>
    </section>
  );
}

function MobileDashboardView({ reports, onOpen }: { reports: Report[]; onOpen: (report: Report) => void }) {
  const pinnedIds = useResultStore((s) => s.pinnedIds);
  const stats = useMemo(() => buildLocalDashboardStats(reports, pinnedIds, MAX_LOCAL_REPORTS), [pinnedIds, reports]);
  const totalTokens = stats.totalTokens;
  const storageTone = stats.storageStatus === '가득 참' ? 'text-destructive' : stats.storageStatus === '여유 적음' ? 'text-amber-600' : 'text-primary';

  return (
    <section className="min-h-dvh px-6 pb-28 pt-12">
      <h1 className="mb-6 text-[28px] font-black tracking-[-0.035em]">대시보드</h1>
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="bg-card p-4 shadow-[0_1px_8px_rgba(21,23,31,0.04)]">
          <p className="signal-meta text-[9px] text-muted-foreground/50">총 콘텐츠</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">{reports.length}</p>
          <p className="mt-1 text-[10px] text-emerald-600">로컬 저장</p>
        </div>
        <div className="bg-foreground p-4 text-background shadow-[0_1px_8px_rgba(21,23,31,0.06)]">
          <p className="signal-meta text-[9px] text-background/55">총 토큰</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">{Math.max(0, Math.round(totalTokens / 1000))}<span className="text-primary">k</span></p>
          <p className="mt-1 text-[10px] text-background/55">누적 사용량</p>
        </div>
        <div className="bg-card p-4 shadow-[0_1px_8px_rgba(21,23,31,0.04)]">
          <p className="signal-meta text-[9px] text-muted-foreground/50">평균 글자</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">{stats.avgLength}</p>
          <p className="mt-1 text-[10px] text-muted-foreground/55">콘텐츠 평균</p>
        </div>
        <div className="bg-card p-4 shadow-[0_1px_8px_rgba(21,23,31,0.04)]">
          <p className="signal-meta text-[9px] text-muted-foreground/50">저장 공간</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">{reports.length}<span className="text-base">/{MAX_LOCAL_REPORTS}</span></p>
          <p className={cn('mt-1 text-[10px]', storageTone)}>{stats.storageStatus} · {stats.storagePct}%</p>
        </div>
      </div>

      <div className="mb-4 bg-card p-5 shadow-[0_1px_8px_rgba(21,23,31,0.04)]">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-sm font-black">일별 생성량</h2>
          <span className="signal-meta text-[9px] text-muted-foreground/45">최근 7일</span>
        </div>
        <div className="flex h-28 items-end justify-between gap-3 px-2">
          {stats.activityDays.map((day) => {
            const height = day.count > 0 ? Math.max(10, Math.round((day.count / stats.maxActivityCount) * 86)) : 8;
            return (
              <div key={day.key} className="flex flex-1 flex-col items-center gap-2">
                <div className={cn('w-full max-w-8', day.count > 0 ? 'bg-primary' : 'bg-muted')} style={{ height: `${height}px` }} />
                <span className="signal-meta text-[9px] text-muted-foreground/45">{day.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-card p-5 shadow-[0_1px_8px_rgba(21,23,31,0.04)]">
        <h2 className="mb-4 text-sm font-black">스타일 분포</h2>
        {stats.topStyles.length === 0 ? (
          <p className="text-sm text-muted-foreground">아직 생성 결과가 없습니다.</p>
        ) : (
          <div className="space-y-3">
            {stats.topStyles.map(([style, count], index) => {
              const pct = reports.length ? Math.max(8, Math.round((count / reports.length) * 100)) : 0;
              return (
                <div key={style}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-semibold">{getStyleLabel(style)}</span>
                    <span className="text-muted-foreground/55">{pct}%</span>
                  </div>
                  <div className="h-1.5 bg-muted">
                    <div className={cn('h-full', index === 0 ? 'bg-primary' : 'bg-foreground')} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="mt-4 bg-card p-5 shadow-[0_1px_8px_rgba(21,23,31,0.04)]">
        <h2 className="mb-4 text-sm font-black">고정 결과</h2>
        {stats.pinned.length === 0 ? (
          <p className="text-sm text-muted-foreground">중요한 결과를 고정하면 모바일에서도 바로 열 수 있습니다.</p>
        ) : (
          <div className="space-y-2">
            {stats.pinned.slice(0, 3).map((report) => (
              <button
                key={report.id}
                type="button"
                className="block w-full border border-border/70 bg-background px-3 py-3 text-left"
                onClick={() => onOpen(report)}
              >
                <p className="line-clamp-1 text-sm font-black">{report.title || '제목 없음'}</p>
                <p className="signal-meta mt-1 text-[9px] text-muted-foreground/55">{getStyleLabel(report.style)} · {report.time}</p>
              </button>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function MobileDetailView({ report, onBack }: { report: Report; onBack: () => void }) {
  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const noteLanguage = useSettingsStore((s) => s.modifiers.language ?? 'ko');
  const [chatOpen, setChatOpen] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);

  async function handleSaveKnowledgeNote() {
    if (isSavingNote || !report.url) return;
    setIsSavingNote(true);
    try {
      const note = await createKnowledgeNote({
        content: report.transcript?.trim() || report.content,
        language: noteLanguage,
        model: selectedModel || undefined,
        source: {
          type: noteSourceTypeFromUrl(report.url),
          url: report.url,
          title: report.youtube_title || report.title || '학습 소스',
        },
      });
      toast.success('학습 노트로 저장했습니다.', {
        description: '핵심 개념·인용·복습 질문으로 지식위키에 추가했습니다.',
        action: {
          label: '열기',
          onClick: () => {
            window.location.href = `/notes/${encodeURIComponent(note.id)}`;
          },
        },
      });
    } catch (err) {
      const body = isApiError<NoteDuplicateWarning>(err) ? err.body : undefined;
      const duplicate = body?.duplicate_notes?.[0];
      if (isApiError<NoteDuplicateWarning>(err) && err.status === 409 && duplicate?.id) {
        toast.warning(body?.warning || '이미 학습한 자료와 비슷합니다.', {
          description: body?.next_action || '기존 노트를 열어 이어서 확인하세요.',
          action: {
            label: '기존 노트 열기',
            onClick: () => {
              window.location.href = `/notes/${encodeURIComponent(duplicate.id)}`;
            },
          },
        });
      } else {
        toast.error(err instanceof Error ? err.message : '학습 노트 저장에 실패했습니다.');
      }
    } finally {
      setIsSavingNote(false);
    }
  }

  return (
    <>
    <section className="min-h-dvh pb-28">
      <div className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b border-border/50 bg-background/95 px-5 backdrop-blur">
        <button type="button" onClick={onBack} aria-label="뒤로가기" className="-ml-1 flex h-9 w-9 items-center justify-center rounded-full text-muted-foreground">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-black tracking-[-0.02em]">{report.title}</h1>
          <p className="signal-meta mt-0.5 truncate text-[9px] text-muted-foreground/50">{getStyleLabel(report.style)} · {report.time}</p>
        </div>
      </div>

      <article className="px-6 pt-6">
        <p className="signal-meta mb-4 text-[10px] text-muted-foreground/45">{report.time} · AI · {(report.usage?.total_tokens || 0).toLocaleString()} TOKENS</p>
        <h2 className="mb-6 text-[25px] font-black leading-[1.16] tracking-[-0.04em] text-foreground">{report.title}</h2>
        <div className="prose max-w-none text-[15px] leading-[1.9] text-foreground/82 prose-headings:font-black prose-headings:tracking-[-0.03em] prose-h2:text-[20px] prose-h3:text-[17px] prose-strong:bg-primary/10 prose-strong:px-0.5 prose-blockquote:border-l-[3px] prose-blockquote:border-primary prose-blockquote:bg-transparent prose-blockquote:pl-4 prose-blockquote:text-foreground/60 prose-a:text-primary">
          <ReactMarkdown>{report.content}</ReactMarkdown>
        </div>

        <div className="mt-7">
          <p className="signal-meta mb-3 text-[10px] text-muted-foreground/45">지원 스타일</p>
          <div className="flex gap-2 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none]">
            {STYLE_OPTIONS.map((style) => {
              const active = style.id === report.style;
              return (
                <span
                  key={style.id}
                  className={cn(
                    'shrink-0 rounded-full border px-4 py-2 text-xs font-bold',
                    active
                      ? 'border-foreground bg-foreground text-background'
                      : 'border-border/70 bg-card text-foreground/75',
                  )}
                >
                  {style.emoji} {style.label}{active ? ' · 현재' : ''}
                </span>
              );
            })}
          </div>
        </div>

        <div className="mt-5 border border-border/70 bg-card p-4">
          <p className="signal-meta mb-3 text-[10px] text-muted-foreground/45">출처</p>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <span className="h-2.5 w-2.5 rounded-full bg-[#20C997]" />
            <span className="min-w-0 flex-1 truncate">{report.youtube_title || report.url || '생성 콘텐츠'}</span>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground/40" />
          </div>
        </div>

        <div className="mt-6 grid gap-3">
          {report.url && (
            <button
              type="button"
              onClick={handleSaveKnowledgeNote}
              disabled={isSavingNote}
              className="flex w-full items-center justify-center gap-2 rounded-sm border border-border/70 bg-card px-4 py-3 text-sm font-black text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSavingNote ? <Loader2 className="h-4 w-4 animate-spin" /> : <BookOpen className="h-4 w-4" />}
              {isSavingNote ? '노트 저장 중...' : '학습 노트로 저장'}
            </button>
          )}
          <a
            href="/notes"
            className="flex w-full items-center justify-center gap-2 rounded-sm border border-border/70 bg-background px-4 py-3 text-sm font-black text-foreground transition-colors hover:bg-muted"
          >
            <BookOpen className="h-4 w-4" />
            지식위키 열기
            <ExternalLink className="h-3.5 w-3.5 text-muted-foreground/50" />
          </a>
          {report.url && (
            <button
              type="button"
              onClick={() => setChatOpen(true)}
              className="flex w-full items-center justify-center gap-2 rounded-sm border border-foreground bg-primary px-4 py-3 text-sm font-black text-primary-foreground shadow-[3px_3px_0_var(--foreground)] transition-transform active:translate-x-[1px] active:translate-y-[1px] active:shadow-none"
            >
              <MessageSquare className="h-4 w-4" />
              영상에 질문하기
            </button>
          )}
        </div>
      </article>
    </section>
    {chatOpen && report.url && (
      <VideoChatPanel
        videoUrl={report.url}
        videoTitle={report.youtube_title || report.title}
        model={selectedModel || undefined}
        onClose={() => setChatOpen(false)}
      />
    )}
    </>
  );
}

export default function MobileAppShell({
  reports,
  urls,
  isLoading,
  error,
  onAddUrl,
  onRemoveUrl,
  onGenerate,
  inputTab,
  onInputTabChange,
  textValue,
  onTextChange,
  onGenerateText,
}: MobileAppShellProps) {
  const [activeTab, setActiveTab] = useState<MobileTab>('create');
  const [activeReport, setActiveReport] = useState<Report | null>(null);

  if (activeReport) {
    return (
      <div className="min-h-dvh bg-background text-foreground xl:hidden">
        <MobileDetailView report={activeReport} onBack={() => setActiveReport(null)} />
        <MobileBottomNav activeTab="library" onChange={(tab) => { setActiveReport(null); setActiveTab(tab); }} />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-background text-foreground xl:hidden">
      {activeTab === 'create' && (
        <MobileCreateView
          urls={urls}
          isLoading={isLoading}
          error={error}
          onAddUrl={onAddUrl}
          onRemoveUrl={onRemoveUrl}
          onGenerate={onGenerate}
          inputTab={inputTab}
          onInputTabChange={onInputTabChange}
          textValue={textValue}
          onTextChange={onTextChange}
          onGenerateText={onGenerateText}
        />
      )}
      {activeTab === 'library' && <MobileLibraryView reports={reports} onOpen={setActiveReport} />}
      {activeTab === 'dashboard' && <MobileDashboardView reports={reports} onOpen={setActiveReport} />}
      <MobileBottomNav activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}

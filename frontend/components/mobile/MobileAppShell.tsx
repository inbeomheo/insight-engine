'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import ReactMarkdown from 'react-markdown';
import {
  ArrowLeft,
  ArrowUp,
  BarChart3,
  CheckCircle2,
  Grid2X2,
  Loader2,
  MessageSquare,
  PlusCircle,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { STYLE_OPTIONS } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { getStyleLabel } from '@/lib/helpers';
import { useSettingsStore } from '@/stores/settingsStore';
import type { GenerationMode, Report } from '@/lib/types';

type MobileTab = 'create' | 'library' | 'dashboard';

interface MobileAppShellProps {
  reports: Report[];
  urls: string[];
  isLoading: boolean;
  error: string | null;
  onAddUrl: (url: string) => string | null;
  onRemoveUrl: (url: string) => void;
  onGenerate: (draftUrl?: string) => void;
  onSchedule: (report: Report) => void;
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
const PUBLISHING_ENABLED = process.env.NEXT_PUBLIC_PUBLISHING_ENABLED === 'true';
const VideoChatPanel = dynamic(() => import('@/components/chat/VideoChatPanel'), { ssr: false });

function MobileBottomNav({ activeTab, onChange }: { activeTab: MobileTab; onChange: (tab: MobileTab) => void }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 border-t border-[#DDE3F0] bg-white/96 px-4 pb-[calc(env(safe-area-inset-bottom)+0.65rem)] pt-2.5 shadow-[0_-10px_28px_rgba(21,23,31,0.08)] backdrop-blur" aria-label="모바일 하단 네비게이션">
      <div className="mx-auto grid max-w-[430px] grid-cols-3 gap-2">
        {(Object.keys(TAB_META) as MobileTab[]).map((tab) => {
          const Icon = TAB_META[tab].icon;
          const active = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              className={cn(
                'flex min-h-12 flex-col items-center justify-center gap-1 rounded-2xl text-[11px] font-extrabold tracking-[-0.01em] transition-all active:scale-[0.98]',
                active
                  ? 'bg-[#2F54EB] text-white shadow-[0_8px_18px_rgba(47,84,235,0.28)]'
                  : 'text-[#667085] hover:bg-[#F5F6F8]'
              )}
              onClick={() => onChange(tab)}
            >
              <Icon className={cn('h-5 w-5', active && 'stroke-[2.5]')} />
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
}: Pick<MobileAppShellProps, 'urls' | 'isLoading' | 'error' | 'onAddUrl' | 'onRemoveUrl' | 'onGenerate'>) {
  const [draftUrl, setDraftUrl] = useState('');
  const selectedStyle = useSettingsStore((s) => s.selectedStyle);
  const setSelectedStyle = useSettingsStore((s) => s.setSelectedStyle);
  const providers = useSettingsStore((s) => s.providers);
  const selectedProvider = useSettingsStore((s) => s.selectedProvider);
  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const setSelectedProvider = useSettingsStore((s) => s.setSelectedProvider);
  const setSelectedModel = useSettingsStore((s) => s.setSelectedModel);
  const generationMode = useSettingsStore((s) => s.generationMode);
  const setGenerationMode = useSettingsStore((s) => s.setGenerationMode);
  const [inputError, setInputError] = useState('');
  const mobileProviderIds = useMemo(() => {
    const preferred = ['chatmock', 'zhipuai'].filter((id) => providers[id]);
    return preferred.length > 0 ? preferred : Object.keys(providers);
  }, [providers]);
  const activeProviderId = mobileProviderIds.includes(selectedProvider) ? selectedProvider : mobileProviderIds[0] || '';
  const currentModels = activeProviderId ? providers[activeProviderId]?.models || [] : [];
  const activeModelId = currentModels.some((model) => model.id === selectedModel) ? selectedModel : currentModels[0]?.id || '';

  useEffect(() => {
    if (!activeProviderId) return;
    if (selectedProvider !== activeProviderId) {
      setSelectedProvider(activeProviderId);
    }
    if (activeModelId && selectedModel !== activeModelId) {
      setSelectedModel(activeModelId);
    }
  }, [activeProviderId, activeModelId, selectedProvider, selectedModel, setSelectedProvider, setSelectedModel]);

  const selectMobileProvider = (providerId: string) => {
    setSelectedProvider(providerId);
    const firstModel = providers[providerId]?.models?.[0];
    if (firstModel) setSelectedModel(firstModel.id);
  };

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
    setSelectedStyle(selectedStyle === styleId && styleId !== 'blog_seo' ? 'blog_seo' : styleId);
  };

  const canGenerate = !isLoading && (urls.length > 0 || Boolean(draftUrl.trim()));
  const generateCount = Math.max(1, urls.length || (draftUrl.trim() ? 1 : 0));

  return (
    <section className="mx-auto min-h-[100svh] max-w-[430px] px-4 pb-[calc(env(safe-area-inset-bottom)+17rem)] pt-7">
      <div className="mb-6 rounded-[28px] border border-[#DDE3F0] bg-white px-4 py-4 shadow-[0_12px_32px_rgba(21,23,31,0.08)]">
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-2xl bg-[#15171F] shadow-[0_8px_16px_rgba(21,23,31,0.18)]">
              <span className="h-3 w-3 rounded-full bg-[#2F54EB]" />
            </span>
            <span className="text-[16px] font-black tracking-[-0.03em] text-[#15171F]">Insight Engine</span>
          </div>
          <span className="rounded-full bg-[#F5F6F8] px-2.5 py-1 text-[10px] font-extrabold text-[#667085]">MOBILE</span>
        </div>

        <p className="mb-2 text-[11px] font-black tracking-[0.08em] text-[#2F54EB]">새 분석 · STEP 01</p>
        <h1 className="text-[31px] font-black leading-[1.05] tracking-[-0.055em] text-[#15171F]">
          어떤 영상을<br />콘텐츠로 만들까?
        </h1>
      </div>

      <div className="mb-2 flex min-h-[60px] items-center gap-2 rounded-[22px] border border-[#C9D3EA] bg-white px-3 shadow-[0_10px_24px_rgba(47,84,235,0.10)] focus-within:border-[#2F54EB]">
        <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-[#2F54EB]" />
        <input
          className="min-w-0 flex-1 bg-transparent text-[15px] font-semibold text-[#15171F] outline-none placeholder:text-[#98A2B3]"
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
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[#2F54EB] text-white shadow-[0_8px_16px_rgba(47,84,235,0.26)] transition-transform active:scale-[0.96]"
          onClick={submitDraft}
          aria-label="URL 추가"
        >
          <ArrowUp className="h-5 w-5" />
        </button>
      </div>
      <div className="mb-4 flex flex-wrap gap-1.5 text-[11px] font-bold text-[#667085]">
        <span className="rounded-full bg-white px-2.5 py-1">YouTube</span><span className="rounded-full bg-white px-2.5 py-1">웹</span><span className="rounded-full bg-white px-2.5 py-1">RSS</span><span className="rounded-full bg-white px-2.5 py-1">arXiv</span><span className="rounded-full bg-white px-2.5 py-1">Podcast</span>
      </div>
      {(inputError || error) && (
        <p className="mb-3 rounded-sm border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">{inputError || error}</p>
      )}

      {urls.length > 0 && (
        <div className="mb-5 space-y-2">
          {urls.map((url) => (
            <div key={url} className="flex min-h-12 items-center gap-2 rounded-2xl border border-[#DDE3F0] bg-white px-3 text-xs text-[#667085] shadow-[0_6px_18px_rgba(21,23,31,0.05)]">
              <span className="h-2 w-2 shrink-0 rounded-full bg-[#2F54EB]" />
              <span className="min-w-0 flex-1 truncate font-semibold text-[#15171F]/80">{url}</span>
              <span className="rounded-full bg-[#EEF3FF] px-2 py-0.5 text-[9px] font-black text-[#2F54EB]">YouTube</span>
              <button type="button" onClick={() => onRemoveUrl(url)} aria-label="URL 제거">
                <X className="h-4 w-4 text-muted-foreground/45" />
              </button>
            </div>
          ))}
        </div>
      )}

      {mobileProviderIds.length > 0 && (
        <div className="mb-5 rounded-[24px] border border-[#DDE3F0] bg-white p-4 shadow-[0_10px_26px_rgba(21,23,31,0.06)]">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-sm font-black text-[#15171F]">AI 모델</h2>
            <span className="text-[10px] font-bold text-[#2F54EB]">GLM · ChatMock</span>
          </div>
          <div className="mb-3 grid grid-cols-2 gap-2">
            {mobileProviderIds.map((providerId) => {
              const active = activeProviderId === providerId;
              return (
                <button
                  key={providerId}
                  type="button"
                  className={cn(
                    'min-h-11 rounded-2xl border px-3 text-left text-xs font-black transition-all active:scale-[0.98]',
                    active
                      ? 'border-[#2F54EB] bg-[#EEF3FF] text-[#2F54EB] shadow-[0_8px_18px_rgba(47,84,235,0.16)]'
                      : 'border-[#DDE3F0] bg-[#F8FAFF] text-[#667085]'
                  )}
                  onClick={() => selectMobileProvider(providerId)}
                >
                  {providers[providerId]?.name || providerId}
                </button>
              );
            })}
          </div>
          <div className="grid gap-2">
            {currentModels.map((model) => {
              const active = activeModelId === model.id;
              return (
                <button
                  key={model.id}
                  type="button"
                  className={cn(
                    'min-h-10 rounded-2xl border px-3 text-left text-xs font-extrabold transition-all active:scale-[0.98]',
                    active
                      ? 'border-[#15171F] bg-[#15171F] text-white'
                      : 'border-[#DDE3F0] bg-white text-[#344054]'
                  )}
                  onClick={() => setSelectedModel(model.id)}
                >
                  {model.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="mb-6 rounded-[24px] border border-[#DDE3F0] bg-white p-4 shadow-[0_10px_26px_rgba(21,23,31,0.06)]">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="text-sm font-black text-[#15171F]">출력 스타일 <span className="text-[#98A2B3]">{STYLE_OPTIONS.length}</span></h2>
          <span className="text-right text-[10px] font-bold leading-tight text-[#2F54EB]">다시 누르면<br />기본값</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {STYLE_OPTIONS.map((style) => {
            const active = selectedStyle === style.id;
            return (
              <button
                key={style.id}
                type="button"
                aria-pressed={active}
                title={active && style.id !== 'blog_seo' ? '다시 누르면 Blog+SEO 기본값으로 돌아가요' : undefined}
                className={cn(
                  'min-h-10 rounded-2xl border px-3 text-left text-xs font-extrabold transition-all active:scale-[0.98]',
                  active
                    ? 'border-[#2F54EB] bg-[#2F54EB] text-white shadow-[0_8px_18px_rgba(47,84,235,0.24)]'
                    : 'border-[#DDE3F0] bg-[#F8FAFF] text-[#344054]'
                )}
                onClick={() => handleStyleSelect(style.id)}
              >
                <span className="mr-1.5">{style.emoji}</span>{style.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mb-7 rounded-[24px] border border-[#DDE3F0] bg-white p-4 shadow-[0_10px_26px_rgba(21,23,31,0.06)]">
        <h2 className="mb-3 text-sm font-black text-[#15171F]">생성 모드</h2>
        <div className="grid grid-cols-3 gap-1 rounded-2xl bg-[#F5F6F8] p-1">
          {(['individual', 'combined', 'fusion'] as GenerationMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={cn(
                'min-h-11 rounded-xl text-sm font-black transition-all active:scale-[0.98]',
                generationMode === mode ? 'bg-white text-[#2F54EB] shadow-[0_6px_14px_rgba(21,23,31,0.08)]' : 'text-[#667085]'
              )}
              onClick={() => setGenerationMode(mode)}
            >
              {MODE_LABELS[mode]}
            </button>
          ))}
        </div>
      </div>

      <div className="h-24" aria-hidden="true" />

      <div className="fixed inset-x-0 bottom-[calc(env(safe-area-inset-bottom)+5.75rem)] z-40 px-4 xl:hidden">
        <div className="mx-auto max-w-[430px] rounded-[26px] border border-[#C9D3EA] bg-white/95 p-2 shadow-[0_-12px_32px_rgba(21,23,31,0.14)] backdrop-blur">
          <Button
            className="min-h-14 w-full rounded-[20px] bg-[#2F54EB] text-base font-black text-white shadow-[0_14px_28px_rgba(47,84,235,0.28)] hover:bg-[#2548D8] active:scale-[0.99] disabled:bg-[#B8C4E6]"
            disabled={!canGenerate}
            onClick={handleGenerateClick}
          >
            {isLoading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : null}
            콘텐츠 생성 <span className="ml-1 text-xs opacity-80">×{generateCount}</span>
          </Button>
        </div>
      </div>
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
    <section className="mx-auto min-h-[100svh] max-w-[430px] px-4 pb-[calc(env(safe-area-inset-bottom)+14rem)] pt-7">
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
              className="block w-full border border-border/70 bg-card px-4 py-4 text-left shadow-[0_1px_8px_rgba(23,21,15,0.04)] transition-transform active:scale-[0.99]"
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

function MobileDashboardView({ reports }: { reports: Report[] }) {
  const styleCounts = useMemo(() => {
    return STYLE_OPTIONS.slice(0, 3).map((style) => ({ ...style, count: reports.filter((r) => r.style === style.id).length }));
  }, [reports]);
  const totalTokens = reports.reduce((sum, report) => sum + (report.usage?.total_tokens || 0), 0);

  return (
    <section className="mx-auto min-h-[100svh] max-w-[430px] px-4 pb-[calc(env(safe-area-inset-bottom)+14rem)] pt-7">
      <h1 className="mb-6 text-[28px] font-black tracking-[-0.035em]">대시보드</h1>
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="bg-card p-4 shadow-[0_1px_8px_rgba(23,21,15,0.04)]">
          <p className="signal-meta text-[9px] text-muted-foreground/50">총 콘텐츠</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">{reports.length}</p>
          <p className="mt-1 text-[10px] text-emerald-600">▲ 최근 기록</p>
        </div>
        <div className="bg-foreground p-4 text-background shadow-[0_1px_8px_rgba(23,21,15,0.06)]">
          <p className="signal-meta text-[9px] text-background/55">총 토큰</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">{Math.max(0, Math.round(totalTokens / 1000))}<span className="text-primary">k</span></p>
          <p className="mt-1 text-[10px] text-background/55">누적 사용량</p>
        </div>
        <div className="bg-card p-4 shadow-[0_1px_8px_rgba(23,21,15,0.04)]">
          <p className="signal-meta text-[9px] text-muted-foreground/50">평균 글자</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">{reports.length ? Math.round(reports.reduce((s, r) => s + r.content.length, 0) / reports.length) : 0}</p>
          <p className="mt-1 text-[10px] text-muted-foreground/55">콘텐츠 평균</p>
        </div>
        <div className="bg-card p-4 shadow-[0_1px_8px_rgba(23,21,15,0.04)]">
          <p className="signal-meta text-[9px] text-muted-foreground/50">QA 통과율</p>
          <p className="mt-3 text-[30px] font-black tracking-[-0.05em]">96<span className="text-base">%</span></p>
          <p className="mt-1 text-[10px] text-primary">지표 5</p>
        </div>
      </div>

      <div className="mb-4 bg-card p-5 shadow-[0_1px_8px_rgba(23,21,15,0.04)]">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-sm font-black">일별 생성량</h2>
          <span className="signal-meta text-[9px] text-muted-foreground/45">최근 7일</span>
        </div>
        <div className="flex h-28 items-end justify-between gap-3 px-2">
          {[45, 62, 38, 86, 68, 54, 34].map((height, index) => (
            <div key={index} className="flex flex-1 flex-col items-center gap-2">
              <div className={cn('w-full max-w-8', index === 3 ? 'bg-primary' : 'bg-[#EEE9E0]')} style={{ height: `${height}px` }} />
              <span className="signal-meta text-[9px] text-muted-foreground/45">{'월화수목금토일'[index]}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-card p-5 shadow-[0_1px_8px_rgba(23,21,15,0.04)]">
        <h2 className="mb-4 text-sm font-black">스타일 분포</h2>
        <div className="space-y-3">
          {styleCounts.map((style, index) => {
            const pct = reports.length ? Math.max(8, Math.round((style.count / reports.length) * 100)) : [58, 22, 13][index];
            return (
              <div key={style.id}>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="font-semibold">{style.label}</span>
                  <span className="text-muted-foreground/55">{pct}%</span>
                </div>
                <div className="h-1.5 bg-[#EEE9E0]">
                  <div className={cn('h-full', index === 0 ? 'bg-primary' : 'bg-foreground')} style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function MobileDetailView({ report, onBack, onSchedule }: { report: Report; onBack: () => void; onSchedule: (report: Report) => void }) {
  const [chatOpen, setChatOpen] = useState(false);
  return (
    <section className="min-h-[100svh] pb-[calc(env(safe-area-inset-bottom)+14rem)]">
      {chatOpen && report.url && (
        <VideoChatPanel
          videoUrl={report.url}
          videoTitle={report.youtube_title || report.title}
          onClose={() => setChatOpen(false)}
        />
      )}
      <div className="sticky top-0 z-40 border-b border-[#DDE3F0] bg-white/96 px-4 py-3 shadow-[0_8px_24px_rgba(21,23,31,0.06)] backdrop-blur">
        <div className="mx-auto flex max-w-[430px] items-center gap-2.5">
          <button type="button" onClick={onBack} aria-label="뒤로가기" className="-ml-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-[#F5F6F8] text-[#667085]">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-black tracking-[-0.02em] text-[#15171F]">{report.title}</h1>
            <p className="mt-0.5 truncate text-[10px] font-bold text-[#667085]">{getStyleLabel(report.style)} · {report.time}</p>
          </div>
          {report.url && (
            <Button size="sm" variant="outline" className="h-10 shrink-0 rounded-2xl border-[#C9D3EA] bg-[#EEF3FF] px-3 text-xs font-black text-[#2F54EB]" onClick={() => setChatOpen(true)}>
              <MessageSquare className="mr-1.5 h-3.5 w-3.5" />
              질문
            </Button>
          )}
          {PUBLISHING_ENABLED && (
            <Button size="sm" className="h-10 shrink-0 rounded-2xl bg-[#2F54EB] px-3 text-xs font-black text-white" onClick={() => onSchedule(report)}>
              발행
            </Button>
          )}
        </div>
      </div>

      <article className="mx-auto max-w-[430px] px-4 pt-6">
        <p className="signal-meta mb-4 text-[10px] text-muted-foreground/45">{report.time} · AI · {(report.usage?.total_tokens || 0).toLocaleString()} TOKENS</p>
        <h2 className="mb-6 text-[25px] font-black leading-[1.16] tracking-[-0.04em] text-foreground">{report.title}</h2>
        <div className="prose max-w-none text-[15px] leading-[1.9] text-foreground/82 prose-headings:font-black prose-headings:tracking-[-0.03em] prose-h2:text-[20px] prose-h3:text-[17px] prose-strong:bg-primary/10 prose-strong:px-0.5 prose-blockquote:border-l-[3px] prose-blockquote:border-primary prose-blockquote:bg-transparent prose-blockquote:pl-4 prose-blockquote:text-foreground/60 prose-a:text-primary">
          <ReactMarkdown>{report.content}</ReactMarkdown>
        </div>

        <div className="mt-7 flex gap-2 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none]">
          {['요약', '튜토리얼', 'Q&A', '앱 아이디어'].map((label) => (
            <span key={label} className="shrink-0 rounded-full border border-border/70 bg-card px-4 py-2 text-xs font-bold text-foreground/75">{label} →</span>
          ))}
        </div>

        <div className="mt-5 border border-border/70 bg-card p-4">
          <p className="signal-meta mb-3 text-[10px] text-muted-foreground/45">출처</p>
          <div className="flex items-center gap-2 text-sm font-semibold">
            <span className="h-2.5 w-2.5 rounded-full bg-[#20C997]" />
            <span className="min-w-0 flex-1 truncate">{report.youtube_title || report.url || '생성 콘텐츠'}</span>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground/40" />
          </div>
        </div>
      </article>
    </section>
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
  onSchedule,
}: MobileAppShellProps) {
  const [activeTab, setActiveTab] = useState<MobileTab>('create');
  const [activeReport, setActiveReport] = useState<Report | null>(null);

  if (activeReport) {
    return (
      <div className="fixed inset-0 overflow-y-auto overscroll-contain bg-[#F5F6F8] text-foreground [-webkit-overflow-scrolling:touch] xl:hidden">
        <MobileDetailView report={activeReport} onBack={() => setActiveReport(null)} onSchedule={onSchedule} />
        <MobileBottomNav activeTab="library" onChange={(tab) => { setActiveReport(null); setActiveTab(tab); }} />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 overflow-y-auto overscroll-contain bg-[#F5F6F8] text-foreground [-webkit-overflow-scrolling:touch] xl:hidden">
      {activeTab === 'create' && (
        <MobileCreateView
          urls={urls}
          isLoading={isLoading}
          error={error}
          onAddUrl={onAddUrl}
          onRemoveUrl={onRemoveUrl}
          onGenerate={onGenerate}
        />
      )}
      {activeTab === 'library' && <MobileLibraryView reports={reports} onOpen={setActiveReport} />}
      {activeTab === 'dashboard' && <MobileDashboardView reports={reports} />}
      <MobileBottomNav activeTab={activeTab} onChange={setActiveTab} />
    </div>
  );
}

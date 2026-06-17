'use client';

import { useCallback, useEffect, useMemo, useRef, useState, startTransition, useDeferredValue } from 'react';
import dynamic from 'next/dynamic';
import { Sparkles, Youtube, Layers, Combine, Bot, AlertCircle, Loader2, Plus, CalendarDays, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import UrlInput from '@/components/input/UrlInput';
import SettingsPopover from '@/components/settings/SettingsPopover';
import SettingsModal from '@/components/settings/SettingsModal';
import ResultCard from '@/components/result/ResultCard';
import ViewModeSelector from '@/components/result/ViewModeSelector';
import FilterBar from '@/components/result/FilterBar';
import LoadingSkeleton from '@/components/result/LoadingSkeleton';
import FusionProgress from '@/components/result/FusionProgress';
import GenerationModeSelector from '@/components/input/GenerationModeSelector';
import FusionOptions from '@/components/input/FusionOptions';

// Phase 1: 모달 + 캘린더 dynamic import (초기 번들 축소)
const PromptModal = dynamic(() => import('@/components/modals/PromptModal'), { ssr: false });
const MindmapModal = dynamic(() => import('@/components/modals/MindmapModal'), { ssr: false });
const OnboardingModal = dynamic(() => import('@/components/modals/OnboardingModal'), { ssr: false });
const CustomStyleModal = dynamic(() => import('@/components/modals/CustomStyleModal'), { ssr: false });
const WorkspaceSettingsModal = dynamic(() => import('@/components/modals/WorkspaceSettingsModal'), { ssr: false });
const TemplateGalleryModal = dynamic(() => import('@/components/modals/TemplateGalleryModal'), { ssr: false });
const ScheduleModal = dynamic(() => import('@/components/modals/ScheduleModal'), { ssr: false });
const ContentCalendar = dynamic(() => import('@/components/schedule/ContentCalendar'), { ssr: false });
const GuidedTour = dynamic(() => import('@/components/onboarding/GuidedTour'), { ssr: false });
const HelpPanel = dynamic(() => import('@/components/help/HelpPanel'), { ssr: false });


import { useSettingsStore } from '@/stores/settingsStore';
import { useResultStore } from '@/stores/resultStore';
import { useUIStore } from '@/stores/uiStore';
import { cn } from '@/lib/utils';
import { useProviders } from '@/hooks/useProviders';
import { useGenerate } from '@/hooks/useGenerate';
import { useUrls } from '@/hooks/useUrls';
import { useSchedule } from '@/hooks/useSchedule';
import { useMcpPlugins } from '@/hooks/useMcpPlugins';
import { useTranslation } from '@/hooks/useTranslation';
import { isOnboardingDone } from '@/lib/storage';
import type { Report, ViewMode } from '@/lib/types';

export default function Home() {
  const hydrateSettings = useSettingsStore((s) => s.hydrate);
  const hydrateResults = useResultStore((s) => s.hydrate);
  const reports = useResultStore((s) => s.reports);
  const searchQuery = useResultStore((s) => s.searchQuery);
  const styleFilter = useResultStore((s) => s.styleFilter);

  const settingsPopoverOpen = useUIStore((s) => s.settingsPopoverOpen);
  const setSettingsPopoverOpen = useUIStore((s) => s.setSettingsPopoverOpen);
  const setOnboardingOpen = useUIStore((s) => s.setOnboardingOpen);
  const activeReportId = useUIStore((s) => s.activeReportId);
  const activeView = useUIStore((s) => s.activeView);
  const setActiveView = useUIStore((s) => s.setActiveView);
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen);
  const setSettingsModalOpen = useUIStore((s) => s.setSettingsModalOpen);

  const generationMode = useSettingsStore((s) => s.generationMode);
  const enableAgentMode = useSettingsStore((s) => s.enableAgentMode);
  const setEnableAgentMode = useSettingsStore((s) => s.setEnableAgentMode);
  const { urls, addUrl, addUrls, removeUrl } = useUrls();
  const { isLoading, error, generateBatchUrls, generateMergedUrls, generateFusionUrls } = useGenerate();
  const { schedules, removeSchedule, addSchedule, isLoading: scheduleLoading } = useSchedule(activeView === 'calendar');

  // MCP 플러그인 — 페이지 레벨에서 1회 로드, 모든 카드에 공유
  const mcpPlugins = useMcpPlugins();
  const { t } = useTranslation();

  // 뷰 모드 — localStorage 연동
  const [viewMode, setViewMode] = useState<ViewMode>('full');
  useEffect(() => {
    const saved = localStorage.getItem('ie_view_mode') as ViewMode | null;
    if (saved && ['compact', 'full', 'timeline'].includes(saved)) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setViewMode(saved);
    }
  }, []);
  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
    localStorage.setItem('ie_view_mode', mode);
  }, []);

  // 예약 발행 모달 — 페이지 레벨 1개 (카드마다 마운트 X)
  const [scheduleTarget, setScheduleTarget] = useState<Report | null>(null);
  const handleScheduleOpen = useCallback((report: Report) => {
    setScheduleTarget(report);
  }, []);

  // onExpandToFull — 안정 참조 (인라인 화살표 함수 방지 → memo 유지)
  const handleExpandToFull = useCallback(() => handleViewModeChange('full'), [handleViewModeChange]);

  // onToggleSettings — 안정 참조 (UrlInput memo 유지)
  const handleToggleSettings = useCallback(() => setSettingsPopoverOpen(!settingsPopoverOpen), [settingsPopoverOpen, setSettingsPopoverOpen]);

  // filteredReports — 메모이제이션 (매 렌더마다 새 배열 생성 방지)
  const filtered = useMemo(() => {
    const lowerQuery = searchQuery?.toLowerCase();
    return reports.filter((r) => {
      if (styleFilter && r.style !== styleFilter) return false;
      if (!lowerQuery) return true;
      return (
        r.title.toLowerCase().includes(lowerQuery) ||
        r.content.toLowerCase().includes(lowerQuery)
      );
    });
  }, [reports, searchQuery, styleFilter]);

  // 카드 목록 점진적 렌더링 — 첫 렌더 시 5개만, 나머지는 idle 시점에 추가
  const INITIAL_RENDER_COUNT = 5;
  const [visibleCount, setVisibleCount] = useState(INITIAL_RENDER_COUNT);
  const deferredFiltered = useDeferredValue(filtered);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setVisibleCount(INITIAL_RENDER_COUNT);
  }, [searchQuery, styleFilter]);

  const handleLoadMore = useCallback(() => {
    setVisibleCount((prev) => Math.min(prev + 5, deferredFiltered.length));
  }, [deferredFiltered.length]);

  // ScheduleModal 핸들러 — 안정 참조
  const handleScheduleOpenChange = useCallback((open: boolean) => {
    if (!open) setScheduleTarget(null);
  }, []);

  const handleScheduleSubmit = useCallback(async (data: { target_plugin: string; scheduled_at: string }) => {
    const target = scheduleTarget;
    if (!target) return;
    const ok = await addSchedule({
      title: target.title,
      content: target.content,
      html: target.html,
      ...data,
    });
    if (ok) setScheduleTarget(null);
  }, [scheduleTarget, addSchedule]);

  // 도움말 패널 + 가이드 투어
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourActive, setTourActive] = useState(false);

  // HelpPanel + GuidedTour 핸들러 — 안정 참조
  const handleCloseHelp = useCallback(() => setHelpOpen(false), []);
  const handleCloseTour = useCallback(() => setTourActive(false), []);

  // 전체 페이지 드래그앤드롭
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounter = useRef(0);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current++;
    if (dragCounter.current === 1) setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current--;
    if (dragCounter.current === 0) setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      dragCounter.current = 0;
      setIsDragOver(false);

      const text =
        e.dataTransfer.getData('text/uri-list') ||
        e.dataTransfer.getData('text/plain') ||
        '';

      // 텍스트에서 URL 모두 추출 (YouTube, 웹페이지, RSS, arXiv)
      const urlPattern = /https?:\/\/[^\s]+/g;
      const matches = text.match(urlPattern);
      if (!matches) return;

      for (const url of matches) {
        addUrl(url.trim());
      }
    },
    [addUrl],
  );

  // 프로바이더 로드
  useProviders();

  // localStorage 복원
  useEffect(() => {
    hydrateSettings();
    hydrateResults();

    // 온보딩 체크
    if (!isOnboardingDone()) {
      setOnboardingOpen(true);
    }
  }, [hydrateSettings, hydrateResults, setOnboardingOpen]);

  // 생성 시작 (1개면 단일, 여러 개면 배치)
  const handleGenerate = useCallback(async () => {
    if (urls.length === 0) return;
    const submitted = [...urls];
    const ok = await generateBatchUrls(submitted);
    if (ok) startTransition(() => submitted.forEach(removeUrl));
  }, [urls, generateBatchUrls, removeUrl]);

  // 합쳐서 생성 (여러 URL → 1개 통합 카드)
  const handleGenerateMerged = useCallback(async () => {
    if (urls.length < 2) return;
    const submitted = [...urls];
    const ok = await generateMergedUrls(submitted);
    if (ok) startTransition(() => submitted.forEach(removeUrl));
  }, [urls, generateMergedUrls, removeUrl]);

  // 퓨전 분석 (2~5개 URL → 교차분석 + 웹리서치)
  const handleGenerateFusion = useCallback(async () => {
    if (urls.length < 2) return;
    const submitted = [...urls];
    const ok = await generateFusionUrls(submitted);
    if (ok) startTransition(() => submitted.forEach(removeUrl));
  }, [urls, generateFusionUrls, removeUrl]);

  return (
    <div
      className="flex h-screen overflow-hidden relative"
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* 스킵 내비게이션 (접근성) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-lg focus:text-sm"
      >
        본문으로 건너뛰기
      </a>
      {/* 드래그 오버레이 */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-md border-2 border-dashed border-primary/50 rounded-xl pointer-events-none animate-fade-in shadow-inner">
          <div className="flex flex-col items-center gap-3 text-primary">
            <Youtube className="h-12 w-12 opacity-60 animate-bounce" />
            <p className="text-lg font-medium">{t('urlInput.dragDrop')}</p>
          </div>
        </div>
      )}

      {/* 사이드바 */}
      <Sidebar />

      {/* 메인 영역 */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header />

        {/* 콘텐츠 */}
        <main className="flex-1 overflow-hidden" id="main-content" role="main">
          <ScrollArea className="h-full">
            <div className="px-4 pb-24 pt-5 sm:px-8 sm:pt-10 lg:px-14 lg:pb-10">

              {/* 캘린더 뷰 */}
              {activeView === 'calendar' && (
                <div className="max-w-3xl mx-auto">
                  <h2 className="text-xl font-semibold mb-6">{t('calendar.title')}</h2>
                  <ContentCalendar schedules={schedules} onDelete={removeSchedule} />
                </div>
              )}

              {/* 메인 뷰 (콘텐츠 생성) */}
              {activeView === 'main' && <>
              {/* URL 입력 영역 */}
              <section className="relative mb-12 max-w-[880px]">
                <div className="mb-6 space-y-3">
                  <p className="signal-meta text-[11px] font-semibold text-primary">새 분석 · STEP 01</p>
                  <h1 className="max-w-[720px] text-[30px] font-bold leading-[1.08] tracking-[-0.025em] text-foreground sm:text-[38px]">
                    어떤 영상을<br className="hidden sm:block" /> 콘텐츠로 만들까요?
                  </h1>
                  <p className="max-w-[560px] text-sm leading-6 text-muted-foreground">
                    YouTube, 웹페이지, RSS, arXiv, Podcast를 한 번에 모아 요약·글쓰기·발행-ready 문서로 변환해요.
                  </p>
                </div>

                <div className="relative max-w-[720px]">
                  <UrlInput
                    urls={urls}
                    onAddUrl={addUrl}
                    onAddUrls={addUrls}
                    onRemoveUrl={removeUrl}
                    onToggleSettings={handleToggleSettings}
                    isLoading={isLoading}
                    onGenerate={handleGenerate}
                  />
                  <SettingsPopover />
                </div>

                {/* 생성 모드 선택 + 퓨전 옵션 */}
                {urls.length >= 2 && (
                  <div className="mt-4 max-w-[720px] animate-fade-in">
                    <GenerationModeSelector />
                    <FusionOptions />
                  </div>
                )}
              </section>

              {/* 생성 버튼 (URL이 있을 때) */}
              {urls.length > 0 && (
                <div className="mb-6 flex max-w-[720px] flex-wrap gap-2 sm:gap-3 animate-fade-in" role="group" aria-label="콘텐츠 생성 버튼">
                  {generationMode === 'individual' && (
                    <Button
                      onClick={handleGenerate}
                      className="h-[50px] gap-2 px-7 text-sm font-semibold"
                      size="lg"
                    >
                      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                      {urls.length === 1
                        ? t('generateButton.singleUrl')
                        : t('generateButton.multipleUrls', { count: urls.length })}
                      {isLoading && <span className="text-xs opacity-70">+</span>}
                    </Button>
                  )}
                  {generationMode === 'combined' && urls.length >= 2 && (
                    <Button
                      onClick={handleGenerateMerged}
                      variant="outline"
                      className="h-[50px] gap-2 rounded-sm border-primary/40 px-7 text-sm font-semibold text-primary hover:bg-primary/5"
                      size="lg"
                    >
                      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers className="h-4 w-4" />}
                      {t('generateButton.combined', { count: urls.length })}
                      {isLoading && <span className="text-xs opacity-70">+</span>}
                    </Button>
                  )}
                  {generationMode === 'fusion' && urls.length >= 2 && (
                    <Button
                      onClick={handleGenerateFusion}
                      variant="outline"
                      className="h-[50px] gap-2 rounded-sm border-[#7C5CFF]/40 px-7 text-sm font-semibold text-[#7C5CFF] hover:bg-[#7C5CFF]/10"
                      size="lg"
                    >
                      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Combine className="h-4 w-4" />}
                      {t('generateButton.fusion', { count: urls.length })}
                      {isLoading && <span className="text-xs opacity-70">+</span>}
                    </Button>
                  )}
                  {/* URL 1개 + combined/fusion 모드일 때 개별 분석 fallback */}
                  {urls.length === 1 && generationMode !== 'individual' && (
                    <Button
                      onClick={handleGenerate}
                      className="h-[50px] gap-2 px-7 text-sm font-semibold"
                      size="lg"
                    >
                      {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                      {t('generateButton.singleUrl')}
                      {isLoading && <span className="text-xs opacity-70">+</span>}
                    </Button>
                  )}
                </div>
              )}

              {/* 에이전트 모드 토글 */}
              {urls.length > 0 && generationMode === 'individual' && (
                <div className="mb-3 flex max-w-[720px] animate-fade-in">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={enableAgentMode}
                    aria-label="에이전트 모드 토글"
                    onClick={() => setEnableAgentMode(!enableAgentMode)}
                    className={cn(
                      'signal-meta flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[10px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
                      enableAgentMode
                        ? 'bg-primary/10 border-primary/40 text-primary'
                        : 'bg-muted/40 border-border/40 text-muted-foreground hover:text-foreground'
                    )}
                  >
                    <Bot className="h-3.5 w-3.5" />
                    에이전트 모드 {enableAgentMode ? 'ON' : 'OFF'}
                  </button>
                </div>
              )}

              {/* 에러 */}
              {error && (
                <div
                  role="alert"
                  aria-live="polite"
                  className="mb-4 flex w-full items-center gap-2 rounded-sm border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive animate-fade-in"
                >
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  {error}
                </div>
              )}

              {/* 필터 + 뷰 모드 선택 */}
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <FilterBar />
                {reports.length > 0 && (
                  <ViewModeSelector mode={viewMode} onChange={handleViewModeChange} />
                )}
              </div>

              {/* 결과 카드 / 빈 상태 */}
              <div className="w-full space-y-4">
                {isLoading && generationMode === 'fusion' && (
                  <FusionProgress isLoading={isLoading} isFusion={true} />
                )}
                {isLoading && <LoadingSkeleton />}

                {deferredFiltered.slice(0, visibleCount).map((r) => (
                  <div
                    key={r.id}
                    data-report-id={r.id}
                    className={cn(
                      'transition-all duration-300',
                      activeReportId === r.id && 'rounded-sm ring-2 ring-primary/30'
                    )}
                  >
                    <ResultCard
                      report={r}
                      searchQuery={searchQuery}
                      mcpPlugins={mcpPlugins}
                      onSchedule={handleScheduleOpen}
                      viewMode={viewMode}
                      onExpandToFull={handleExpandToFull}
                    />
                  </div>
                ))}
                {visibleCount < deferredFiltered.length && (
                  <div className="text-center py-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleLoadMore}
                      className="gap-2 text-xs hover:shadow-md active:scale-[0.98] transition-all duration-200"
                    >
                      <Layers className="h-3.5 w-3.5" />
                      더 보기 ({deferredFiltered.length - visibleCount}개 남음)
                    </Button>
                  </div>
                )}

                {/* 빈 상태 */}
                {!isLoading && reports.length === 0 && (
                  <div className="text-center py-12 sm:py-24">
                    <div className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-sm border border-border bg-card">
                      <Youtube className="h-9 w-9 text-primary/45" />
                    </div>
                    <h3 className="font-semibold text-lg text-foreground/80 mb-2">{t('emptyState.title')}</h3>
                    <p className="text-sm text-muted-foreground/60 leading-relaxed">
                      {t('emptyState.description').split('\n').map((line, i) => (
                        <span key={i}>{line}{i === 0 && <br />}</span>
                      ))}
                    </p>
                  </div>
                )}
              </div>
              </>}
            </div>
          </ScrollArea>
        </main>
      </div>

      {/* 모바일 커맨드 네비게이션 */}
      <nav
        className="fixed inset-x-3 bottom-3 z-40 flex items-center justify-between rounded-full border border-border bg-card/95 p-1 shadow-[0_8px_30px_rgba(23,21,15,0.12)] lg:hidden"
        aria-label="모바일 빠른 이동"
      >
        <button
          type="button"
          className={cn(
            'signal-meta flex h-10 flex-1 items-center justify-center gap-1.5 rounded-full text-[10px] font-semibold transition-colors',
            activeView === 'main' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground'
          )}
          onClick={() => { setActiveView('main'); setSidebarOpen(false); }}
        >
          <Plus className="h-3.5 w-3.5" />
          새 분석
        </button>
        <button
          type="button"
          className={cn(
            'signal-meta flex h-10 flex-1 items-center justify-center gap-1.5 rounded-full text-[10px] font-semibold transition-colors',
            activeView === 'calendar' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground'
          )}
          onClick={() => { setActiveView('calendar'); setSidebarOpen(false); }}
        >
          <CalendarDays className="h-3.5 w-3.5" />
          캘린더
        </button>
        <button
          type="button"
          className="signal-meta flex h-10 flex-1 items-center justify-center gap-1.5 rounded-full text-[10px] font-semibold text-muted-foreground transition-colors hover:text-foreground"
          onClick={() => setSettingsModalOpen(true)}
        >
          <Settings className="h-3.5 w-3.5" />
          설정
        </button>
      </nav>

      {/* 모달 */}
      <SettingsModal />
      <PromptModal />
      <MindmapModal />
      <OnboardingModal />
      <CustomStyleModal />
      <WorkspaceSettingsModal />
      <TemplateGalleryModal />

      {/* 도움말 패널 */}
      <HelpPanel open={helpOpen} onClose={handleCloseHelp} />

      {/* 가이드 투어 */}
      <GuidedTour forceStart={tourActive} onClose={handleCloseTour} />

      {/* 예약 발행 모달 — 페이지 레벨 1개 */}
      <ScheduleModal
        open={!!scheduleTarget}
        onOpenChange={handleScheduleOpenChange}
        title={scheduleTarget?.title || ''}
        content={scheduleTarget?.content || ''}
        html={scheduleTarget?.html}
        isLoading={scheduleLoading}
        onSchedule={handleScheduleSubmit}
      />
    </div>
  );
}

'use client';

import { useCallback, useEffect, useMemo, useRef, useState, startTransition, useDeferredValue, type KeyboardEvent } from 'react';
import dynamic from 'next/dynamic';
import { Layers, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import SettingsPopover from '@/components/settings/SettingsPopover';
import SettingsModal from '@/components/settings/SettingsModal';
import ResultCard from '@/components/result/ResultCard';
import LoadingSkeleton from '@/components/result/LoadingSkeleton';
import FusionProgress from '@/components/result/FusionProgress';
import StudioShell from '@/components/studio/StudioShell';
import StudioHero from '@/components/studio/StudioHero';
import SourceComposer, { type SourceComposerSnapshot } from '@/components/studio/SourceComposer';
import OutputBlueprint from '@/components/studio/OutputBlueprint';
import GenerateDock from '@/components/studio/GenerateDock';
import StudioRightPanel from '@/components/studio/StudioRightPanel';
import StudioResultToolbar from '@/components/studio/StudioResultToolbar';
import WorkbenchEmptyState from '@/components/studio/WorkbenchEmptyState';

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
import { useTranslation } from '@/hooks/useTranslation';
import { isOnboardingDone } from '@/lib/storage';
import type { Report, ViewMode } from '@/lib/types';

const EMPTY_SOURCE_DRAFT: SourceComposerSnapshot = {
  mode: 'url',
  text: '',
  textValid: false,
  file: null,
  audioFile: null,
};

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

  const selectedProvider = useSettingsStore((s) => s.selectedProvider);
  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const modelLabel = selectedModel || selectedProvider || '자동 선택';

  const generationMode = useSettingsStore((s) => s.generationMode);
  const { urls, addUrl, addUrls, removeUrl, clearUrls, reorderUrls } = useUrls();
  const { isLoading, error, generateFromText, generateFromFile, generateFromAudio, generateBatchUrls, generateMergedUrls, generateFusionUrls } = useGenerate();
  const { schedules, removeSchedule, addSchedule, isLoading: scheduleLoading } = useSchedule(activeView === 'calendar');
  const [sourceDraft, setSourceDraft] = useState<SourceComposerSnapshot>(EMPTY_SOURCE_DRAFT);
  const [sourceComposerResetKey, setSourceComposerResetKey] = useState(0);

  // MCP 플러그인 — 페이지 레벨에서 1회 로드, 모든 카드에 공유
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

  const handleScheduleSubmit = useCallback(async (data: { target_plugin: string; scheduled_at: string; options?: Record<string, unknown> }) => {
    const target = scheduleTarget;
    if (!target) return false;
    const ok = await addSchedule({
      title: target.title,
      content: target.content,
      html: target.html,
      ...data,
    });
    if (ok) setScheduleTarget(null);
    return ok;
  }, [scheduleTarget, addSchedule]);

  // 도움말 패널 + 가이드 투어
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourActive, setTourActive] = useState(false);
  const [mobileRightPanelOpen, setMobileRightPanelOpen] = useState(false);
  const mobileRightPanelCloseRef = useRef<HTMLButtonElement | null>(null);
  const mobileRightPanelSheetRef = useRef<HTMLElement | null>(null);

  // HelpPanel + GuidedTour 핸들러 — 안정 참조
  const handleToggleHelp = useCallback(() => setHelpOpen((open) => !open), []);
  const handleCloseHelp = useCallback(() => {
    setHelpOpen(false);
    requestAnimationFrame(() => {
      const trigger = document.querySelector("[data-testid='header-help-trigger']");
      if (trigger instanceof HTMLButtonElement) trigger.focus();
    });
  }, []);
  const handleStartTour = useCallback(() => {
    setHelpOpen(false);
    setTourActive(true);
  }, []);
  const handleCloseTour = useCallback(() => {
    setTourActive(false);
    requestAnimationFrame(() => {
      const trigger = document.querySelector("[data-testid='header-help-trigger']");
      if (trigger instanceof HTMLButtonElement) trigger.focus();
    });
  }, []);
  const handleOpenMobileRightPanel = useCallback(() => setMobileRightPanelOpen(true), []);
  const handleCloseMobileRightPanel = useCallback(() => {
    setMobileRightPanelOpen(false);
    requestAnimationFrame(() => {
      const trigger = document.querySelector("[data-testid='mobile-right-panel-trigger']");
      if (trigger instanceof HTMLButtonElement) trigger.focus();
    });
  }, []);
  const handleMobileRightPanelKeyDown = useCallback((event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      handleCloseMobileRightPanel();
      return;
    }
    if (event.key !== 'Tab') return;

    const sheet = mobileRightPanelSheetRef.current;
    if (!sheet) return;
    const focusable = Array.from(
      sheet.querySelectorAll<HTMLElement>(
        'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((element) => element.tabIndex >= 0);
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || !sheet.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }, [handleCloseMobileRightPanel]);

  useEffect(() => {
    if (!mobileRightPanelOpen) return;
    const frame = requestAnimationFrame(() => mobileRightPanelCloseRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [mobileRightPanelOpen]);

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

      addUrls(matches.map((url) => url.trim()));
    },
    [addUrls],
  );

  const handleFocusSourceComposer = useCallback(() => {
    const target = document.querySelector('#url-input');
    if (target instanceof HTMLInputElement) {
      target.focus({ preventScroll: true });
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      requestAnimationFrame(() => target.focus({ preventScroll: true }));
    } else {
      target?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, []);

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

  useEffect(() => {
    function handleNewAnalysisReset() {
      clearUrls();
      setSourceDraft(EMPTY_SOURCE_DRAFT);
      setSourceComposerResetKey((key) => key + 1);
    }

    window.addEventListener('insight-engine-new-analysis', handleNewAnalysisReset);
    return () => window.removeEventListener('insight-engine-new-analysis', handleNewAnalysisReset);
  }, [clearUrls]);

  // 생성 시작 (1개면 단일, 여러 개면 배치)
  const handleGenerate = useCallback(async () => {
    if (urls.length === 0) return;
    const submitted = [...urls];
    const ok = await generateBatchUrls(submitted);
    if (ok) startTransition(() => submitted.forEach(removeUrl));
  }, [urls, generateBatchUrls, removeUrl]);

  const handleGenerateStudio = useCallback(async () => {
    if (sourceDraft.mode === 'url' && urls.length > 0) {
      await handleGenerate();
      return;
    }
    if (sourceDraft.mode === 'text' && sourceDraft.textValid) {
      await generateFromText(sourceDraft.text);
      return;
    }
    if (sourceDraft.mode === 'file' && sourceDraft.file) {
      await generateFromFile(sourceDraft.file);
      return;
    }
    if (sourceDraft.mode === 'voice' && sourceDraft.audioFile) {
      await generateFromAudio(sourceDraft.audioFile);
    }
  }, [urls.length, handleGenerate, sourceDraft, generateFromText, generateFromFile, generateFromAudio]);

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

  const studioSourceCount =
    sourceDraft.mode === 'url'
      ? urls.length
      : sourceDraft.mode === 'text'
        ? (sourceDraft.textValid ? 1 : 0)
        : sourceDraft.mode === 'file'
          ? (sourceDraft.file ? 1 : 0)
          : (sourceDraft.audioFile ? 1 : 0);
  const studioSourceLabel =
    sourceDraft.mode === 'url'
      ? (urls.length > 0 ? 'URL 소스' : 'URL 소스 대기')
      : sourceDraft.mode === 'text'
        ? (sourceDraft.textValid ? '텍스트 소스' : '텍스트 소스 준비 중')
        : sourceDraft.mode === 'file'
          ? (sourceDraft.file ? `파일 소스 · ${sourceDraft.file.name}` : '파일 소스 대기')
          : (sourceDraft.audioFile ? `음성 소스 · ${sourceDraft.audioFile.name}` : '음성 소스 대기');
  const studioGenerationMode = sourceDraft.mode === 'url' && urls.length >= 2 ? generationMode : 'individual';

  return (
    <>
      {isDragOver && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-md border-2 border-dashed border-primary/50 pointer-events-none animate-fade-in shadow-inner">
          <div className="flex flex-col items-center gap-3 text-primary">
            <Layers className="h-12 w-12 opacity-60 animate-bounce" />
            <p className="text-lg font-medium">{t('urlInput.dragDrop')}</p>
          </div>
        </div>
      )}

      <StudioShell
        className="relative"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        sidebar={<Sidebar />}
        header={<Header modelLabel={modelLabel} isLoading={isLoading} sourceCount={studioSourceCount} onOpenRightPanel={handleOpenMobileRightPanel} rightPanelOpen={mobileRightPanelOpen} onOpenHelp={handleToggleHelp} helpOpen={helpOpen} />}
        rightPanel={<StudioRightPanel reports={reports} sourceCount={studioSourceCount} schedulesCount={schedules.length} generationMode={studioGenerationMode} />}
        main={(
          <>
            <a
              href="#main-content"
              className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-lg focus:text-sm"
            >
              본문으로 이동
            </a>

            <StudioHero modelLabel={modelLabel} resultCount={reports.length} />

            {activeView === 'calendar' ? (
              <section className="rounded-[24px] border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/60">
                <h2 className="mb-6 text-xl font-semibold">{t('calendar.title')}</h2>
                <ContentCalendar schedules={schedules} onDelete={removeSchedule} />
              </section>
            ) : (
              <>
                <div className="relative">
                  <SourceComposer
                    key={sourceComposerResetKey}
                    urls={urls}
                    onAddUrl={addUrl}
                    onAddUrls={addUrls}
                    onRemoveUrl={removeUrl}
                    onReorderUrl={reorderUrls}
                    onToggleSettings={handleToggleSettings}
                    isLoading={isLoading}
                    onGenerateUrl={handleGenerate}
                    onGenerateText={generateFromText}
                    onGenerateFile={generateFromFile}
                    onGenerateAudio={generateFromAudio}
                    onStateChange={setSourceDraft}
                  />
                  <SettingsPopover />
                </div>

                <OutputBlueprint sourceMode={sourceDraft.mode} sourceCount={studioSourceCount} />

                {error && (
                  <div
                    role="alert"
                    aria-live="polite"
                    className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 shadow-sm shadow-red-100"
                  >
                    {error}
                  </div>
                )}

                <StudioResultToolbar
                  totalCount={reports.length}
                  filteredCount={deferredFiltered.length}
                  visibleCount={visibleCount}
                  viewMode={viewMode}
                  onViewModeChange={handleViewModeChange}
                />

                <div className="space-y-4">
                  {isLoading && studioGenerationMode === 'fusion' && <FusionProgress isLoading={isLoading} isFusion={true} />}
                  {isLoading && <LoadingSkeleton />}

                  {deferredFiltered.slice(0, visibleCount).map((r) => (
                    <div
                      key={r.id}
                      data-report-id={r.id}
                      data-focused={activeReportId === r.id ? 'true' : undefined}
                      className={cn(
                        'transition-all duration-300',
                        activeReportId === r.id && 'rounded-2xl ring-2 ring-primary/30 shadow-md shadow-primary/5'
                      )}
                    >
                      <ResultCard
                        report={r}
                        searchQuery={searchQuery}
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

                  {!isLoading && reports.length === 0 && (
                    <WorkbenchEmptyState onFocusSource={handleFocusSourceComposer} />
                  )}
                </div>

                <GenerateDock
                  sourceCount={studioSourceCount}
                  sourceLabel={studioSourceLabel}
                  mode={studioGenerationMode}
                  isLoading={isLoading}
                  onGenerate={handleGenerateStudio}
                  onGenerateMerged={handleGenerateMerged}
                  onGenerateFusion={handleGenerateFusion}
                />
              </>
            )}
          </>
        )}
      />

      {mobileRightPanelOpen && (
        <div
          id="mobile-right-panel"
          data-testid="mobile-right-panel"
          role="dialog"
          aria-modal="true"
          aria-labelledby="mobile-right-panel-title"
          className="fixed inset-0 z-[70] xl:hidden"
          onKeyDown={handleMobileRightPanelKeyDown}
        >
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/35 backdrop-blur-sm"
            aria-label="작업 패널 닫기"
            onClick={handleCloseMobileRightPanel}
            tabIndex={-1}
          />
          <aside ref={mobileRightPanelSheetRef} className="absolute right-0 top-0 h-full w-[min(360px,92vw)] border-l border-slate-200 bg-white shadow-2xl">
            <div className="flex h-14 items-center justify-between border-b border-slate-200 px-4">
              <p id="mobile-right-panel-title" data-testid="mobile-right-panel-title" className="text-sm font-semibold text-slate-950">작업 패널</p>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                data-testid="mobile-right-panel-close"
                ref={mobileRightPanelCloseRef}
                className="h-8 w-8"
                onClick={handleCloseMobileRightPanel}
                aria-label="작업 패널 닫기"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="h-[calc(100%-3.5rem)]">
              <StudioRightPanel reports={reports} sourceCount={studioSourceCount} schedulesCount={schedules.length} generationMode={studioGenerationMode} />
            </div>
          </aside>
        </div>
      )}


      <SettingsModal />
      <PromptModal />
      <MindmapModal />
      <OnboardingModal />
      <CustomStyleModal />
      <WorkspaceSettingsModal />
      <TemplateGalleryModal />
      <HelpPanel open={helpOpen} onClose={handleCloseHelp} onStartTour={handleStartTour} />
      <GuidedTour forceStart={tourActive} onClose={handleCloseTour} />
      <ScheduleModal
        open={!!scheduleTarget}
        onOpenChange={handleScheduleOpenChange}
        title={scheduleTarget?.title || ''}
        content={scheduleTarget?.content || ''}
        html={scheduleTarget?.html}
        isLoading={scheduleLoading}
        onSchedule={handleScheduleSubmit}
      />
    </>
  );
}

'use client';

import { useCallback, useEffect, useMemo, useRef, useState, startTransition, useDeferredValue } from 'react';
import dynamic from 'next/dynamic';
import { Youtube, Layers, X } from 'lucide-react';
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
  const { urls, addUrl, addUrls, removeUrl } = useUrls();
  const { isLoading, error, generateFromText, generateFromFile, generateFromAudio, generateBatchUrls, generateMergedUrls, generateFusionUrls } = useGenerate();
  const { schedules, removeSchedule, addSchedule, isLoading: scheduleLoading } = useSchedule(activeView === 'calendar');
  const [sourceDraft, setSourceDraft] = useState<SourceComposerSnapshot>({
    mode: 'url',
    text: '',
    textValid: false,
    file: null,
    audioFile: null,
  });

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
  const [mobileRightPanelOpen, setMobileRightPanelOpen] = useState(false);

  // HelpPanel + GuidedTour 핸들러 — 안정 참조
  const handleCloseHelp = useCallback(() => setHelpOpen(false), []);
  const handleCloseTour = useCallback(() => setTourActive(false), []);
  const handleOpenMobileRightPanel = useCallback(() => setMobileRightPanelOpen(true), []);
  const handleCloseMobileRightPanel = useCallback(() => setMobileRightPanelOpen(false), []);

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
  const studioGenerationMode = sourceDraft.mode === 'url' ? generationMode : 'individual';

  return (
    <>
      {isDragOver && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-md border-2 border-dashed border-primary/50 pointer-events-none animate-fade-in shadow-inner">
          <div className="flex flex-col items-center gap-3 text-primary">
            <Youtube className="h-12 w-12 opacity-60 animate-bounce" />
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
        header={<Header modelLabel={modelLabel} isLoading={isLoading} sourceCount={studioSourceCount} onOpenRightPanel={handleOpenMobileRightPanel} />}
        rightPanel={<StudioRightPanel reports={reports} sourceCount={studioSourceCount} schedulesCount={schedules.length} />}
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
                    urls={urls}
                    onAddUrl={addUrl}
                    onAddUrls={addUrls}
                    onRemoveUrl={removeUrl}
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

                <OutputBlueprint />

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
                  {isLoading && generationMode === 'fusion' && <FusionProgress isLoading={isLoading} isFusion={true} />}
                  {isLoading && <LoadingSkeleton />}

                  {deferredFiltered.slice(0, visibleCount).map((r) => (
                    <div
                      key={r.id}
                      data-report-id={r.id}
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
                    <div className="rounded-[28px] border border-dashed border-slate-300 bg-white/60 p-10 text-center">
                      <Youtube className="mx-auto mb-4 h-10 w-10 text-indigo-300" />
                      <h3 className="text-lg font-semibold">아직 결과가 없습니다</h3>
                      <p className="mt-2 text-sm text-slate-500">소스를 추가하고 콘텐츠를 생성하면 여기에 작업 카드가 표시됩니다.</p>
                    </div>
                  )}
                </div>

                <GenerateDock
                  sourceCount={studioSourceCount}
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
        <div data-testid="mobile-right-panel" className="fixed inset-0 z-[70] xl:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/35 backdrop-blur-sm"
            aria-label="작업 패널 닫기"
            onClick={handleCloseMobileRightPanel}
          />
          <aside className="absolute right-0 top-0 h-full w-[min(360px,92vw)] border-l border-slate-200 bg-white shadow-2xl">
            <div className="flex h-14 items-center justify-between border-b border-slate-200 px-4">
              <p className="text-sm font-semibold text-slate-950">작업 패널</p>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                data-testid="mobile-right-panel-close"
                className="h-8 w-8"
                onClick={handleCloseMobileRightPanel}
                aria-label="작업 패널 닫기"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="h-[calc(100%-3.5rem)]">
              <StudioRightPanel reports={reports} sourceCount={studioSourceCount} schedulesCount={schedules.length} />
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
      <HelpPanel open={helpOpen} onClose={handleCloseHelp} />
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

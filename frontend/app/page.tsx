'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { Sparkles, Youtube, Layers, Combine, Bot } from 'lucide-react';
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
  const { hydrate: hydrateSettings } = useSettingsStore();
  const hydrateResults = useResultStore((s) => s.hydrate);
  const reports = useResultStore((s) => s.reports);
  const searchQuery = useResultStore((s) => s.searchQuery);
  const styleFilter = useResultStore((s) => s.styleFilter);

  const { settingsPopoverOpen, setSettingsPopoverOpen, setOnboardingOpen, activeReportId, activeView } =
    useUIStore();

  const { generationMode, enableAgentMode, setEnableAgentMode } = useSettingsStore();
  const { urls, addUrl, addUrls, removeUrl, clearUrls } = useUrls();
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

  // filteredReports — 메모이제이션 (매 렌더마다 새 배열 생성 방지)
  const filtered = useMemo(() => {
    return reports.filter((r) => {
      const matchStyle = !styleFilter || r.style === styleFilter;
      const matchSearch =
        !searchQuery ||
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.content.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStyle && matchSearch;
    });
  }, [reports, searchQuery, styleFilter]);

  // 도움말 패널 + 가이드 투어
  const [helpOpen, setHelpOpen] = useState(false);
  const [tourActive, setTourActive] = useState(false);

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
  async function handleGenerate() {
    if (urls.length === 0) return;
    const ok = await generateBatchUrls([...urls]);
    if (ok) clearUrls();
  }

  // 합쳐서 생성 (여러 URL → 1개 통합 카드)
  async function handleGenerateMerged() {
    if (urls.length < 2) return;
    const ok = await generateMergedUrls([...urls]);
    if (ok) clearUrls();
  }

  // 퓨전 분석 (2~5개 URL → 교차분석 + 웹리서치)
  async function handleGenerateFusion() {
    if (urls.length < 2) return;
    const ok = await generateFusionUrls([...urls]);
    if (ok) clearUrls();
  }

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
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-md border-2 border-dashed border-primary/40 rounded-lg pointer-events-none animate-fade-in">
          <div className="flex flex-col items-center gap-3 text-primary">
            <Youtube className="h-12 w-12 opacity-60" />
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
            <div className="px-4 sm:px-8 lg:px-12 py-4 sm:py-6">

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
              <div className="relative mb-10">
                <UrlInput
                  urls={urls}
                  onAddUrl={addUrl}
                  onAddUrls={addUrls}
                  onRemoveUrl={removeUrl}
                  onToggleSettings={() => setSettingsPopoverOpen(!settingsPopoverOpen)}
                  isLoading={isLoading}
                  onGenerate={handleGenerate}
                />
                <SettingsPopover />

                {/* 생성 모드 선택 + 퓨전 옵션 */}
                {urls.length >= 2 && (
                  <div className="mt-3 animate-fade-in">
                    <GenerationModeSelector />
                    <FusionOptions />
                  </div>
                )}
              </div>

              {/* 생성 버튼 (URL이 있을 때) */}
              {urls.length > 0 && (
                <div className="flex justify-center gap-2 sm:gap-3 mb-4 sm:mb-6 flex-wrap animate-fade-in">
                  {generationMode === 'individual' && (
                    <Button
                      onClick={handleGenerate}
                      disabled={isLoading}
                      className="gap-2 gradient-primary hover:opacity-90 transition-opacity shadow-md px-6 h-11 rounded-xl text-sm font-medium"
                      size="lg"
                    >
                      <Sparkles className="h-4 w-4" />
                      {isLoading
                        ? t('generateButton.loading')
                        : urls.length === 1
                          ? t('generateButton.singleUrl')
                          : t('generateButton.multipleUrls', { count: urls.length })}
                    </Button>
                  )}
                  {generationMode === 'combined' && urls.length >= 2 && (
                    <Button
                      onClick={handleGenerateMerged}
                      disabled={isLoading}
                      variant="outline"
                      className="gap-2 hover:bg-primary/5 border-primary/30 text-primary shadow-sm px-6 h-11 rounded-xl text-sm font-medium"
                      size="lg"
                    >
                      <Layers className="h-4 w-4" />
                      {isLoading ? t('generateButton.loading') : t('generateButton.combined', { count: urls.length })}
                    </Button>
                  )}
                  {generationMode === 'fusion' && urls.length >= 2 && (
                    <Button
                      onClick={handleGenerateFusion}
                      disabled={isLoading}
                      variant="outline"
                      className="gap-2 hover:bg-purple-500/10 border-purple-400/30 text-purple-500 shadow-sm px-6 h-11 rounded-xl text-sm font-medium"
                      size="lg"
                    >
                      <Combine className="h-4 w-4" />
                      {isLoading ? t('generateButton.fusionLoading') : t('generateButton.fusion', { count: urls.length })}
                    </Button>
                  )}
                  {/* URL 1개 + combined/fusion 모드일 때 개별 분석 fallback */}
                  {urls.length === 1 && generationMode !== 'individual' && (
                    <Button
                      onClick={handleGenerate}
                      disabled={isLoading}
                      className="gap-2 gradient-primary hover:opacity-90 transition-opacity shadow-md px-6 h-11 rounded-xl text-sm font-medium"
                      size="lg"
                    >
                      <Sparkles className="h-4 w-4" />
                      {isLoading ? t('generateButton.loading') : t('generateButton.singleUrl')}
                    </Button>
                  )}
                </div>
              )}

              {/* 에이전트 모드 토글 */}
              {urls.length > 0 && generationMode === 'individual' && (
                <div className="flex justify-center mb-2 animate-fade-in">
                  <button
                    type="button"
                    onClick={() => setEnableAgentMode(!enableAgentMode)}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors',
                      enableAgentMode
                        ? 'bg-violet-500/10 border-violet-400/40 text-violet-500'
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
                <div className="w-full mb-4 p-3 bg-destructive/5 border border-destructive/20 rounded-xl text-sm text-destructive animate-fade-in">
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

                {filtered.map((r) => (
                  <div
                    key={r.id}
                    data-report-id={r.id}
                    className={cn(
                      'transition-all duration-300',
                      activeReportId === r.id && 'ring-2 ring-primary/30 rounded-xl'
                    )}
                  >
                    <ResultCard
                      report={r}
                      searchQuery={searchQuery}
                      mcpPlugins={mcpPlugins}
                      onSchedule={handleScheduleOpen}
                      viewMode={viewMode}
                      onExpandToFull={() => handleViewModeChange('full')}
                    />
                  </div>
                ))}

                {/* 빈 상태 */}
                {!isLoading && reports.length === 0 && (
                  <div className="text-center py-12 sm:py-24">
                    <div className="w-20 h-20 mx-auto mb-5 bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center rounded-3xl border border-indigo-100/50">
                      <Youtube className="h-9 w-9 text-indigo-300" />
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

      {/* 모달 */}
      <SettingsModal />
      <PromptModal />
      <MindmapModal />
      <OnboardingModal />
      <CustomStyleModal />
      <WorkspaceSettingsModal />
      <TemplateGalleryModal />

      {/* 도움말 패널 */}
      <HelpPanel open={helpOpen} onClose={() => setHelpOpen(false)} />

      {/* 가이드 투어 */}
      <GuidedTour forceStart={tourActive} onClose={() => setTourActive(false)} />

      {/* 예약 발행 모달 — 페이지 레벨 1개 */}
      <ScheduleModal
        open={!!scheduleTarget}
        onOpenChange={(open) => { if (!open) setScheduleTarget(null); }}
        title={scheduleTarget?.title || ''}
        content={scheduleTarget?.content || ''}
        html={scheduleTarget?.html}
        isLoading={scheduleLoading}
        onSchedule={async (data) => {
          if (!scheduleTarget) return;
          const ok = await addSchedule({
            title: scheduleTarget.title,
            content: scheduleTarget.content,
            html: scheduleTarget.html,
            ...data,
          });
          if (ok) setScheduleTarget(null);
        }}
      />
    </div>
  );
}

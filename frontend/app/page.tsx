'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Sparkles, Youtube, Layers, Combine } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import UrlInput from '@/components/input/UrlInput';
import SettingsPopover from '@/components/settings/SettingsPopover';
import SettingsModal from '@/components/settings/SettingsModal';
import ResultCard from '@/components/result/ResultCard';
import FilterBar from '@/components/result/FilterBar';
import LoadingSkeleton from '@/components/result/LoadingSkeleton';
import FusionProgress from '@/components/result/FusionProgress';
import GenerationModeSelector from '@/components/input/GenerationModeSelector';
import FusionOptions from '@/components/input/FusionOptions';
import PromptModal from '@/components/modals/PromptModal';
import MindmapModal from '@/components/modals/MindmapModal';
import OnboardingModal from '@/components/modals/OnboardingModal';
import CustomStyleModal from '@/components/modals/CustomStyleModal';
import WorkspaceSettingsModal from '@/components/modals/WorkspaceSettingsModal';

import { YOUTUBE_URL_REGEX } from '@/lib/constants';
import { useSettingsStore } from '@/stores/settingsStore';
import { useResultStore } from '@/stores/resultStore';
import { useUIStore } from '@/stores/uiStore';
import { cn } from '@/lib/utils';
import { useProviders } from '@/hooks/useProviders';
import { useGenerate } from '@/hooks/useGenerate';
import { useUrls } from '@/hooks/useUrls';
import { isOnboardingDone } from '@/lib/storage';

export default function Home() {
  const { hydrate: hydrateSettings } = useSettingsStore();
  const { hydrate: hydrateResults, reports, searchQuery, styleFilter } = useResultStore();
  const { settingsPopoverOpen, setSettingsPopoverOpen, setOnboardingOpen, activeReportId } =
    useUIStore();

  const filteredReports = useMemo(() => {
    return reports.filter((r) => {
      const matchStyle = !styleFilter || r.style === styleFilter;
      const matchSearch =
        !searchQuery ||
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.content.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStyle && matchSearch;
    });
  }, [reports, searchQuery, styleFilter]);

  const { generationMode } = useSettingsStore();
  const { urls, addUrl, removeUrl, clearUrls } = useUrls();
  const { isLoading, error, generateBatchUrls, generateMergedUrls, generateFusionUrls } = useGenerate();

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

      // 텍스트에서 YouTube URL 모두 추출
      const urlPattern =
        /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)[\w-]+[^\s]*/g;
      const matches = text.match(urlPattern);
      if (!matches) return;

      for (const url of matches) {
        const trimmed = url.trim();
        if (YOUTUBE_URL_REGEX.test(trimmed)) addUrl(trimmed);
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
      {/* 드래그 오버레이 */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/70 backdrop-blur-md border-2 border-dashed border-primary/40 rounded-lg pointer-events-none animate-fade-in">
          <div className="flex flex-col items-center gap-3 text-primary">
            <Youtube className="h-12 w-12 opacity-60" />
            <p className="text-lg font-medium">YouTube URL을 여기에 놓으세요</p>
          </div>
        </div>
      )}

      {/* 사이드바 */}
      <Sidebar />

      {/* 메인 영역 */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header />

        {/* 콘텐츠 */}
        <main className="flex-1 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="px-8 lg:px-12 py-6">
              {/* URL 입력 영역 */}
              <div className="relative mb-10">
                <UrlInput
                  urls={urls}
                  onAddUrl={addUrl}
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
                <div className="flex justify-center gap-3 mb-6 animate-fade-in">
                  {generationMode === 'individual' && (
                    <Button
                      onClick={handleGenerate}
                      disabled={isLoading}
                      className="gap-2 gradient-primary hover:opacity-90 transition-opacity shadow-md px-6 h-11 rounded-xl text-sm font-medium"
                      size="lg"
                    >
                      <Sparkles className="h-4 w-4" />
                      {isLoading
                        ? '생성 중...'
                        : urls.length === 1
                          ? '1개 URL 분석 시작'
                          : `${urls.length}개 URL 각각 분석`}
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
                      {isLoading ? '생성 중...' : `${urls.length}개 URL 합쳐서 분석`}
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
                      {isLoading ? '퓨전 분석 중...' : `${urls.length}개 URL 퓨전 분석`}
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
                      {isLoading ? '생성 중...' : '1개 URL 분석 시작'}
                    </Button>
                  )}
                </div>
              )}

              {/* 에러 */}
              {error && (
                <div className="w-full mb-4 p-3 bg-destructive/5 border border-destructive/20 rounded-xl text-sm text-destructive animate-fade-in">
                  {error}
                </div>
              )}

              {/* 필터 */}
              <FilterBar />

              {/* 결과 카드 / 빈 상태 */}
              <div className="w-full space-y-4">
                {isLoading && generationMode === 'fusion' && (
                  <FusionProgress isLoading={isLoading} isFusion={true} />
                )}
                {isLoading && <LoadingSkeleton />}

                {filteredReports.map((r) => (
                  <div
                    key={r.id}
                    data-report-id={r.id}
                    className={cn(
                      'transition-all duration-300',
                      activeReportId === r.id && 'ring-2 ring-primary/30 rounded-xl'
                    )}
                  >
                    <ResultCard report={r} searchQuery={searchQuery} />
                  </div>
                ))}

                {/* 빈 상태 */}
                {!isLoading && reports.length === 0 && (
                  <div className="text-center py-24">
                    <div className="w-20 h-20 mx-auto mb-5 bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center rounded-3xl border border-indigo-100/50">
                      <Youtube className="h-9 w-9 text-indigo-300" />
                    </div>
                    <h3 className="font-semibold text-lg text-foreground/80 mb-2">YouTube 영상을 분석해보세요</h3>
                    <p className="text-sm text-muted-foreground/60 leading-relaxed">
                      URL을 붙여넣으면 AI가 블로그, 요약, 튜토리얼 등<br />
                      다양한 형식의 콘텐츠를 자동 생성합니다
                    </p>
                  </div>
                )}
              </div>
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
    </div>
  );
}

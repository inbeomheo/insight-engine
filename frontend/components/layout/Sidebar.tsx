'use client';

import { useState, useMemo, useCallback, memo } from 'react';
import Link from 'next/link';
import { Plus, Search, Trash2, Clock, Sparkles, CalendarDays, Eraser, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useUIStore } from '@/stores/uiStore';
import { useResultStore } from '@/stores/resultStore';
import { useIsMobile } from '@/hooks/use-mobile';
import { cn } from '@/lib/utils';
import { getStyleLabel, getStyleEmoji } from '@/lib/helpers';
import { useTranslation } from '@/hooks/useTranslation';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useIsClient } from '@/hooks/useIsClient';
import WorkspaceSelector from './WorkspaceSelector';

/** 히스토리 항목 — memo로 불필요한 리렌더 방지 */
const HistoryItem = memo(function HistoryItem({
  report,
  isActive,
  onClick,
  onDelete,
}: {
  report: { id: string; title: string; time: string; style: string };
  isActive: boolean;
  onClick: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${report.title} 히스토리 보기`}
      aria-current={isActive ? 'true' : undefined}
      className={cn(
        'group flex items-start gap-2.5 px-2.5 py-2.5 rounded-sm cursor-pointer text-xs transition-colors duration-200',
        isActive ? 'bg-sidebar-accent border border-sidebar-border' : 'hover:bg-sidebar-accent border border-transparent'
      )}
      onClick={() => onClick(report.id)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(report.id); } }}
    >
      <span className="text-sm shrink-0 mt-0.5">{getStyleEmoji(report.style)}</span>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-foreground/90 leading-snug line-clamp-2" title={report.title}>
          {report.title}
        </div>
        <div className="signal-meta flex items-center gap-1 text-[9px] text-muted-foreground/60 mt-1">
          <Clock className="h-3 w-3" />
          <span>{report.time}</span>
          <span>·</span>
          <span>{getStyleLabel(report.style)}</span>
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0 transition-opacity"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(report.id);
        }}
        aria-label={`${report.title} 삭제`}
      >
        <Trash2 className="h-3 w-3 text-destructive/60" />
      </Button>
    </div>
  );
});

export default function Sidebar() {
  const { sidebarOpen, setSidebarOpen, activeReportId, setActiveReportId, activeView, setActiveView } = useUIStore();
  const reports = useResultStore((s) => s.reports);
  const removeReport = useResultStore((s) => s.removeReport);
  const clearReports = useResultStore((s) => s.clearReports);
  const isMobile = useIsMobile();
  const isClient = useIsClient();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 200);
  const { t } = useTranslation();

  const handleHistoryClick = useCallback((id: string) => {
    setActiveReportId(id);

    // 필터 초기화 (필터로 카드가 숨겨진 경우 대비)
    const resultState = useResultStore.getState();
    if (resultState.searchQuery || resultState.styleFilter) {
      resultState.setSearchQuery('');
      resultState.setStyleFilter('');
    }

    // DOM 업데이트 후 스크롤
    setTimeout(() => {
      requestAnimationFrame(() => {
        const el = document.querySelector(`[data-report-id="${id}"]`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }, 50);

    if (isMobile) setSidebarOpen(false);
  }, [setActiveReportId, isMobile, setSidebarOpen]);

  const handleDelete = useCallback((id: string) => {
    removeReport(id);
    if (useUIStore.getState().activeReportId === id) setActiveReportId(null);
  }, [removeReport, setActiveReportId]);

  const handleNewAnalysis = useCallback(() => {
    setActiveReportId(null);

    const urlInput = document.getElementById('url-input');
    urlInput?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => urlInput?.focus(), 300);

    if (isMobile) setSidebarOpen(false);
  }, [setActiveReportId, isMobile, setSidebarOpen]);

  const filtered = useMemo(() => {
    if (!debouncedSearch) return reports;
    const q = debouncedSearch.toLowerCase();
    return reports.filter(
      (r) =>
        r.title.toLowerCase().includes(q) ||
        (r.youtube_title || '').toLowerCase().includes(q)
    );
  }, [reports, debouncedSearch]);

  const grouped = useMemo(() => {
    const groups: Record<string, typeof filtered> = {};
    const dateCache = new Map<string, string>();
    for (const r of filtered) {
      // createdAt(timestamp)에서 날짜 부분만 캐시 키로 사용 (toLocaleDateString 호출 최소화)
      const d = new Date(r.createdAt);
      const dayKey = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      let label = dateCache.get(dayKey);
      if (!label) {
        label = d.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
        dateCache.set(dayKey, label);
      }
      if (!groups[label]) groups[label] = [];
      groups[label].push(r);
    }
    return groups;
  }, [filtered]);

  return (
    <>
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-[2px] z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={cn(
          'w-[236px] border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col h-full shrink-0 z-50',
          'transition-all duration-200 ease-out',
          'fixed lg:relative',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:-translate-x-full lg:w-0 lg:border-0 lg:overflow-hidden'
        )}
        role="navigation"
        aria-label="사이드바 내비게이션"
      >
        {/* 새 분석 */}
        <div className="p-3 pb-2">
          <Button className="w-full gap-2 h-[42px] bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90 shadow-none hover:translate-y-0" size="sm" onClick={handleNewAnalysis}>
            <Plus className="h-4 w-4" />
            <span className="font-medium">{t('sidebar.newAnalysis')}</span>
          </Button>
        </div>

        {/* 워크스페이스 */}
        <WorkspaceSelector />

        {/* 검색 */}
        <div className="px-3 pb-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/60" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('sidebar.historySearch')}
              className="pl-8 h-8 rounded-sm text-xs bg-white border-sidebar-border focus:bg-white transition-colors"
            />
          </div>
        </div>

        {/* 히스토리 */}
        <ScrollArea className="flex-1 overflow-hidden">
          {filtered.length === 0 ? (
            <div className="px-3 py-12 text-center">
              <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-sm border border-sidebar-border bg-sidebar-accent">
                <Sparkles className="h-5 w-5 text-primary/40" />
              </div>
              <p className="signal-meta text-[10px] text-muted-foreground/60">
                {reports.length === 0 ? t('sidebar.noHistory') : t('sidebar.noSearchResults')}
              </p>
            </div>
          ) : (
            <div className="px-2 pb-2">
              {Object.entries(grouped).map(([date, items]) => (
                <div key={date}>
                  <div className="signal-meta px-2 py-2 text-[10px] font-semibold text-muted-foreground/60">
                    {date}
                  </div>
                  {items.map((r) => (
                    <HistoryItem
                      key={r.id}
                      report={r}
                      isActive={activeReportId === r.id}
                      onClick={handleHistoryClick}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* 전체 삭제 + 캘린더 + 노트 */}
        <div className="px-3 pb-2 flex flex-col gap-1">
          <Button
            variant={activeView === 'calendar' ? 'secondary' : 'ghost'}
            className="signal-meta h-9 w-full justify-start gap-2 rounded-sm text-[10px]"
            onClick={() => {
              setActiveView(activeView === 'calendar' ? 'main' : 'calendar');
              if (isMobile) setSidebarOpen(false);
            }}
          >
            <CalendarDays className="h-4 w-4" />
            {t('sidebar.calendar')}
          </Button>
          <Button
            asChild
            variant="ghost"
            className="signal-meta h-9 w-full justify-start gap-2 rounded-sm text-[10px]"
          >
            <Link href="/notes" onClick={() => { if (isMobile) setSidebarOpen(false); }}>
              <BookOpen className="h-4 w-4" />
              {t('sidebar.notes')}
            </Link>
          </Button>
          {isClient && reports.length > 0 && (
            <Button
              variant="ghost"
              className="w-full justify-start gap-2 h-9 text-xs text-destructive/60 hover:text-destructive hover:bg-destructive/5"
              onClick={() => {
                if (window.confirm('모든 히스토리를 삭제하시겠습니까?')) {
                  clearReports();
                  setActiveReportId(null);
                }
              }}
            >
              <Eraser className="h-4 w-4" />
              전체 삭제 ({reports.length})
            </Button>
          )}
        </div>

        {/* 하단 브랜딩 */}
        <div className="p-3 border-t border-sidebar-border">
          <p className="signal-meta text-[10px] text-muted-foreground/50 text-center">
            {t('sidebar.poweredBy')}
          </p>
        </div>
      </aside>
    </>
  );
}

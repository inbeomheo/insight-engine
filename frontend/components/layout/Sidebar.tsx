'use client';

import { useState, useMemo, useCallback } from 'react';
import { Plus, Search, Trash2, Clock, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useUIStore } from '@/stores/uiStore';
import { useResultStore } from '@/stores/resultStore';
import { useIsMobile } from '@/hooks/use-mobile';
import { STYLE_OPTIONS } from '@/lib/constants';
import { cn } from '@/lib/utils';
import WorkspaceSelector from './WorkspaceSelector';

function getStyleLabel(styleId: string) {
  return STYLE_OPTIONS.find((s) => s.id === styleId)?.label || styleId;
}

function getStyleEmoji(styleId: string) {
  return STYLE_OPTIONS.find((s) => s.id === styleId)?.emoji || '📄';
}

export default function Sidebar() {
  const { sidebarOpen, setSidebarOpen, activeReportId, setActiveReportId } = useUIStore();
  const { reports, removeReport } = useResultStore();
  const isMobile = useIsMobile();
  const [search, setSearch] = useState('');

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

  const handleNewAnalysis = useCallback(() => {
    setActiveReportId(null);

    const urlInput = document.getElementById('url-input');
    urlInput?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => urlInput?.focus(), 300);

    if (isMobile) setSidebarOpen(false);
  }, [setActiveReportId, isMobile, setSidebarOpen]);

  const filtered = useMemo(() => {
    if (!search) return reports;
    const q = search.toLowerCase();
    return reports.filter(
      (r) =>
        r.title.toLowerCase().includes(q) ||
        (r.youtube_title || '').toLowerCase().includes(q)
    );
  }, [reports, search]);

  const grouped = useMemo(() => {
    const groups: Record<string, typeof filtered> = {};
    for (const r of filtered) {
      const date = new Date(r.createdAt).toLocaleDateString('ko-KR', {
        month: 'long',
        day: 'numeric',
      });
      if (!groups[date]) groups[date] = [];
      groups[date].push(r);
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
          'w-[260px] border-r border-border/60 bg-[#F8FAFC] flex flex-col h-full shrink-0 z-50',
          'transition-all duration-200 ease-out',
          'fixed lg:relative',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:-translate-x-full lg:w-0 lg:border-0 lg:overflow-hidden'
        )}
      >
        {/* 새 분석 */}
        <div className="p-3 pb-2">
          <Button className="w-full gap-2 h-10 gradient-primary hover:opacity-90 transition-opacity shadow-sm" size="sm" onClick={handleNewAnalysis}>
            <Plus className="h-4 w-4" />
            <span className="font-medium">새 분석</span>
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
              placeholder="히스토리 검색..."
              className="pl-8 h-8 text-xs bg-white/70 border-border/50 focus:bg-white transition-colors"
            />
          </div>
        </div>

        {/* 히스토리 */}
        <ScrollArea className="flex-1">
          {filtered.length === 0 ? (
            <div className="px-3 py-12 text-center">
              <div className="w-10 h-10 mx-auto mb-3 bg-accent rounded-xl flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-primary/40" />
              </div>
              <p className="text-xs text-muted-foreground/60">
                {reports.length === 0 ? '분석 히스토리가 없습니다' : '검색 결과가 없습니다'}
              </p>
            </div>
          ) : (
            <div className="px-2 pb-2">
              {Object.entries(grouped).map(([date, items]) => (
                <div key={date}>
                  <div className="px-2 py-2 text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest">
                    {date}
                  </div>
                  {items.map((r) => (
                    <div
                      key={r.id}
                      className={cn(
                        'group flex items-start gap-2.5 px-2.5 py-2.5 rounded-lg cursor-pointer text-xs transition-all duration-150',
                        activeReportId === r.id
                          ? 'bg-primary/10 shadow-sm'
                          : 'hover:bg-white hover:shadow-sm'
                      )}
                      onClick={() => handleHistoryClick(r.id)}
                    >
                      <span className="text-sm shrink-0 mt-0.5">{getStyleEmoji(r.style)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate text-foreground/90 leading-snug">
                          {r.title}
                        </div>
                        <div className="flex items-center gap-1 text-muted-foreground/50 mt-1">
                          <Clock className="h-3 w-3" />
                          <span>{r.time}</span>
                          <span>·</span>
                          <span>{getStyleLabel(r.style)}</span>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0 transition-opacity"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeReport(r.id);
                          if (activeReportId === r.id) setActiveReportId(null);
                        }}
                      >
                        <Trash2 className="h-3 w-3 text-destructive/60" />
                      </Button>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* 하단 브랜딩 */}
        <div className="p-3 border-t border-border/40">
          <p className="text-[10px] text-muted-foreground/30 text-center">
            Powered by AI
          </p>
        </div>
      </aside>
    </>
  );
}

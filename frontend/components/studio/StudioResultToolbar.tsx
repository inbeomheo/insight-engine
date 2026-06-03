'use client';

import FilterBar from '@/components/result/FilterBar';
import ViewModeSelector from '@/components/result/ViewModeSelector';
import type { ViewMode } from '@/lib/types';

interface StudioResultToolbarProps {
  totalCount: number;
  filteredCount: number;
  visibleCount: number;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export default function StudioResultToolbar({
  totalCount,
  filteredCount,
  visibleCount,
  viewMode,
  onViewModeChange,
}: StudioResultToolbarProps) {
  const shownCount = Math.min(visibleCount, filteredCount);

  return (
    <section
      data-testid="studio-result-toolbar"
      className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/60"
    >
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold tracking-[0.12em] text-indigo-600">Result Workbench</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">생성 결과 관리</h2>
          <p className="mt-1 text-sm text-slate-500">
            전체 결과 {totalCount}개 · 표시 중 {shownCount}개 · 필터 결과 {filteredCount}개
          </p>
        </div>
        {totalCount > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500">보기 모드</span>
            <ViewModeSelector mode={viewMode} onChange={onViewModeChange} />
          </div>
        )}
      </div>

      {totalCount > 0 ? (
        <div className="rounded-2xl bg-slate-50 p-3">
          <p className="mb-2 text-xs font-semibold text-slate-500">필터</p>
          <FilterBar />
        </div>
      ) : (
        <div
          data-testid="result-toolbar-empty-notice"
          className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-3 text-sm text-slate-500"
        >
          결과가 생기면 필터와 보기 모드가 표시됩니다.
        </div>
      )}
    </section>
  );
}

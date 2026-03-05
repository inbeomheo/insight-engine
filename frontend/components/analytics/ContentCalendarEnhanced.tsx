/**
 * 콘텐츠 캘린더 강화 스텁 (F6-06)
 * 월/주/일 뷰 + 드래그앤드롭 일정 이동
 */
'use client';

import React, { useState } from 'react';

type ViewMode = 'month' | 'week' | 'day';

interface ScheduledItem {
  id: string;
  title: string;
  date: string; // YYYY-MM-DD
  style: string;
}

interface ContentCalendarEnhancedProps {
  items?: ScheduledItem[];
  onMove?: (id: string, newDate: string) => void;
  onAdd?: (date: string) => void;
}

export function ContentCalendarEnhanced({
  items = [],
  onMove,
  onAdd,
}: ContentCalendarEnhancedProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [currentDate, setCurrentDate] = useState(new Date());

  const formatYearMonth = (d: Date) =>
    `${d.getFullYear()}년 ${d.getMonth() + 1}월`;

  const prevPeriod = () => {
    const d = new Date(currentDate);
    if (viewMode === 'month') d.setMonth(d.getMonth() - 1);
    else if (viewMode === 'week') d.setDate(d.getDate() - 7);
    else d.setDate(d.getDate() - 1);
    setCurrentDate(d);
  };

  const nextPeriod = () => {
    const d = new Date(currentDate);
    if (viewMode === 'month') d.setMonth(d.getMonth() + 1);
    else if (viewMode === 'week') d.setDate(d.getDate() + 7);
    else d.setDate(d.getDate() + 1);
    setCurrentDate(d);
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {(['month', 'week', 'day'] as ViewMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setViewMode(m)}
              className={`px-3 py-1 text-sm rounded transition-colors ${
                viewMode === m
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted'
              }`}
            >
              {m === 'month' ? '월' : m === 'week' ? '주' : '일'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={prevPeriod} className="px-2 hover:bg-muted rounded">‹</button>
          <span className="text-sm font-medium">{formatYearMonth(currentDate)}</span>
          <button onClick={nextPeriod} className="px-2 hover:bg-muted rounded">›</button>
        </div>
        <button
          onClick={() => onAdd?.(currentDate.toISOString().slice(0, 10))}
          className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded"
        >
          + 예약 추가
        </button>
      </div>

      {/* 캘린더 그리드 플레이스홀더 */}
      <div className="rounded-lg border min-h-64 p-4 flex items-center justify-center text-muted-foreground text-sm">
        {viewMode === 'month' && `월간 뷰 (${formatYearMonth(currentDate)}) — 예약된 항목 ${items.length}건`}
        {viewMode === 'week' && `주간 뷰 — 예약된 항목 ${items.length}건`}
        {viewMode === 'day' && `일간 뷰 (${currentDate.toLocaleDateString('ko-KR')}) — 드래그앤드롭 지원`}
      </div>

      {/* 일정 목록 */}
      {items.length > 0 && (
        <ul className="space-y-2">
          {items.slice(0, 5).map((item) => (
            <li key={item.id} className="flex items-center justify-between rounded border px-3 py-2 text-sm">
              <span>{item.date}</span>
              <span className="font-medium truncate max-w-48">{item.title}</span>
              <span className="text-muted-foreground text-xs">{item.style}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

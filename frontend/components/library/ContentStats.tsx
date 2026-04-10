'use client';

/**
 * ContentStats — 콘텐츠 통계 요약 카드 (F8-20)
 *
 * 라이브러리 항목의 상태별 분포, 스타일별 분포, 핀/아카이브 수를 시각화합니다.
 */

import React, { useMemo } from 'react';
import { Pin, Archive, FileText, Star } from 'lucide-react';
import type { KanbanCard } from './KanbanBoard';

interface Props {
  items: KanbanCard[];
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700 flex items-center gap-3">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon className="w-4 h-4 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}

export default function ContentStats({ items }: Props) {
  const stats = useMemo(() => {
    const byStatus: Record<string, number> = {};
    const byStyle: Record<string, number> = {};
    let pinned = 0;
    let archived = 0;

    for (const item of items) {
      byStatus[item.status] = (byStatus[item.status] ?? 0) + 1;
      if (item.style) byStyle[item.style] = (byStyle[item.style] ?? 0) + 1;
      if ((item as unknown as Record<string, unknown>).is_pinned) pinned++;
      if (item.status === 'archived') archived++;
    }

    return { byStatus, byStyle, pinned, archived, total: items.length };
  }, [items]);

  const topStyle = Object.entries(stats.byStyle).sort((a, b) => b[1] - a[1])[0];

  return (
    <div className="space-y-4">
      {/* 요약 카드 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="전체 콘텐츠" value={stats.total} icon={FileText} color="bg-blue-500" />
        <StatCard label="고정됨" value={stats.pinned} icon={Pin} color="bg-yellow-500" />
        <StatCard label="아카이브" value={stats.archived} icon={Archive} color="bg-slate-500" />
        <StatCard
          label={topStyle ? `최다 스타일: ${topStyle[0]}` : '스타일'}
          value={topStyle ? topStyle[1] : 0}
          icon={Star}
          color="bg-green-500"
        />
      </div>

      {/* 상태별 분포 바 */}
      <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">상태별 분포</h3>
        <div className="space-y-2">
          {Object.entries(stats.byStatus).map(([status, count]) => {
            const pct = stats.total > 0 ? Math.round((count / stats.total) * 100) : 0;
            return (
              <div key={status} className="flex items-center gap-2">
                <span className="w-20 text-xs text-slate-500 capitalize">{status}</span>
                <div className="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="w-8 text-xs text-slate-500 text-right">{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 스타일별 분포 */}
      {Object.keys(stats.byStyle).length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl p-4 border border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">스타일별 분포</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.byStyle)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 10)
              .map(([style, count]) => (
                <span
                  key={style}
                  className="text-xs px-2 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-full border border-blue-200 dark:border-blue-800"
                >
                  {style} ({count})
                </span>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}

'use client';

import { CalendarDays, FileText, Sparkles } from 'lucide-react';
import { QUICK_ACTIONS } from './studioConfig';
import type { Report } from '@/lib/types';

interface StudioRightPanelProps {
  reports: Report[];
  sourceCount: number;
  schedulesCount: number;
}

export default function StudioRightPanel({ reports, sourceCount, schedulesCount }: StudioRightPanelProps) {
  const nlmCount = reports.reduce((sum, report) => sum + (report.notebooklm?.artifacts?.length ?? 0), 0);
  const latest = reports.slice(0, 4);
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Workspace</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-950">작업 요약</h2>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{sourceCount}</p><p className="text-slate-500">소스</p></div>
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{reports.length}</p><p className="text-slate-500">결과</p></div>
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{nlmCount}</p><p className="text-slate-500">NLM</p></div>
        </div>
      </section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> 빠른 액션</div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return <div key={action.id} className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-600"><Icon className="mb-2 h-4 w-4 text-indigo-600" />{action.label}</div>;
          })}
        </div>
      </section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><FileText className="h-4 w-4 text-indigo-600" /> 최근 결과</div>
        <div className="mt-3 space-y-2">
          {latest.length === 0 ? <p className="text-xs text-slate-500">아직 생성된 결과가 없습니다.</p> : latest.map((report) => <div key={report.id} className="rounded-2xl bg-slate-50 p-3"><p className="line-clamp-2 text-xs font-medium text-slate-800">{report.title}</p><p className="mt-1 text-[11px] text-slate-500">{report.style}</p></div>)}
        </div>
      </section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><CalendarDays className="h-4 w-4 text-indigo-600" /> 예약</div>
        <p className="mt-2 text-xs text-slate-500">예약된 발행 {schedulesCount}개</p>
      </section>
    </div>
  );
}

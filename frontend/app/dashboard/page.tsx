'use client';

import { useEffect, useMemo, type ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, BarChart3, FileText, Hash, Sparkles, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import OperationsDashboard from '@/components/dashboard/OperationsDashboard';
import { useResultStore } from '@/stores/resultStore';
import { getStyleLabel } from '@/lib/helpers';
import type { Report } from '@/lib/types';

export default function DashboardPage() {
  const hydrateResults = useResultStore((s) => s.hydrate);
  const reports = useResultStore((s) => s.reports);

  useEffect(() => {
    hydrateResults();
  }, [hydrateResults]);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between gap-3">
          <Button asChild variant="ghost" size="sm" className="gap-1.5 -ml-2">
            <Link href="/">
              <ArrowLeft className="h-4 w-4" />
              홈
            </Link>
          </Button>
          <div className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-[10px] font-medium text-primary">
            <BarChart3 className="h-3 w-3" />
            운영 상태
          </div>
        </div>
        <LocalDashboardSummary reports={reports} />
        <OperationsDashboard />
      </div>
    </div>
  );
}

function LocalDashboardSummary({ reports }: { reports: Report[] }) {
  const stats = useMemo(() => {
    const totalTokens = reports.reduce((sum, report) => sum + (report.usage?.total_tokens ?? 0), 0);
    const avgLength = reports.length
      ? Math.round(reports.reduce((sum, report) => sum + report.content.length, 0) / reports.length)
      : 0;
    const styleCounts = new Map<string, number>();
    for (const report of reports) {
      styleCounts.set(report.style, (styleCounts.get(report.style) ?? 0) + 1);
    }
    const topStyles = Array.from(styleCounts.entries())
      .sort(([, a], [, b]) => b - a)
      .slice(0, 4);
    const recent = [...reports]
      .sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0))
      .slice(0, 4);

    return { totalTokens, avgLength, topStyles, recent };
  }, [reports]);

  return (
    <section className="mb-6 space-y-4">
      <div>
        <p className="signal-meta mb-2 text-[10px] font-semibold text-primary">LOCAL ACTIVITY</p>
        <h1 className="text-2xl font-bold tracking-[-0.02em]">내 작업 요약</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          서버 운영 지표와 별개로, 이 브라우저에 저장된 최근 생성 결과를 요약합니다.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <LocalMetric icon={<FileText className="h-4 w-4" />} label="저장된 결과" value={`${reports.length}개`} />
        <LocalMetric icon={<Zap className="h-4 w-4" />} label="누적 토큰" value={stats.totalTokens.toLocaleString()} />
        <LocalMetric icon={<Hash className="h-4 w-4" />} label="평균 길이" value={`${stats.avgLength.toLocaleString()}자`} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <BarChart3 className="h-4 w-4" /> 로컬 스타일 분포
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.topStyles.length === 0 ? (
              <p className="text-sm text-muted-foreground">아직 생성 결과가 없습니다.</p>
            ) : (
              <div className="space-y-2">
                {stats.topStyles.map(([style, count]) => {
                  const pct = reports.length ? Math.round((count / reports.length) * 100) : 0;
                  return (
                    <div key={style} className="flex items-center gap-3">
                      <span className="w-24 truncate text-sm">{getStyleLabel(style)}</span>
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="signal-meta w-12 text-right text-[10px] text-muted-foreground">{count}건</span>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <Sparkles className="h-4 w-4" /> 최근 로컬 결과
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.recent.length === 0 ? (
              <p className="text-sm text-muted-foreground">홈에서 URL이나 텍스트를 생성하면 여기에 쌓입니다.</p>
            ) : (
              <ul className="space-y-2">
                {stats.recent.map((report) => (
                  <li key={report.id} className="rounded-sm border border-border px-3 py-2">
                    <p className="truncate text-sm font-medium">{report.title || '제목 없음'}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      {getStyleLabel(report.style)} · {report.time}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function LocalMetric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <Card className="rounded-sm border-border bg-card shadow-none">
      <CardHeader className="pb-2">
        <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
          {icon}
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <span className="text-3xl font-bold tracking-[-0.03em]">{value}</span>
      </CardContent>
    </Card>
  );
}

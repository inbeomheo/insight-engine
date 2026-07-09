'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { Activity, AlertCircle, ArrowLeft, BarChart3, FileText, Hash, Server, Sparkles, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import OperationsDashboard from '@/components/dashboard/OperationsDashboard';
import { useResultStore } from '@/stores/resultStore';
import { getStyleLabel } from '@/lib/helpers';
import { apiUrl } from '@/lib/api';
import type { Report } from '@/lib/types';

interface HealthStatus {
  status: string;
  environment: string;
  api_version: string;
  request_count: number;
  error_count: number;
  error_rate: number;
  memory_usage_mb?: number | null;
}

export default function DashboardPage() {
  const hydrateResults = useResultStore((s) => s.hydrate);
  const reports = useResultStore((s) => s.reports);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    hydrateResults();
  }, [hydrateResults]);

  useEffect(() => {
    let alive = true;
    fetch(apiUrl('/health'))
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        return data as HealthStatus;
      })
      .then((data) => {
        if (!alive) return;
        setHealth(data);
        setHealthError(null);
      })
      .catch((err) => {
        if (!alive) return;
        setHealthError(err instanceof Error ? err.message : 'API 상태를 확인할 수 없습니다.');
      });
    return () => {
      alive = false;
    };
  }, []);

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
        <SystemHealthCard health={health} error={healthError} />
        <OperationsDashboard />
      </div>
    </div>
  );
}

function SystemHealthCard({ health, error }: { health: HealthStatus | null; error: string | null }) {
  const statusLabel = health?.status === 'healthy' ? '정상' : error ? '확인 필요' : '확인 중';
  const errorRatePct = health ? Math.round((health.error_rate ?? 0) * 1000) / 10 : 0;

  return (
    <section className="mb-6">
      <Card className="rounded-sm border-border bg-card shadow-none">
        <CardHeader>
          <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
            <Server className="h-4 w-4" /> 시스템 건강도
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="flex items-start gap-3 rounded-sm border border-destructive/30 bg-destructive/5 px-3 py-2">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
              <div>
                <p className="text-sm font-medium text-destructive">API 서버 상태 확인 실패</p>
                <p className="mt-1 text-xs text-muted-foreground">{error}</p>
              </div>
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              <HealthMetric label="상태" value={statusLabel} />
              <HealthMetric label="환경" value={health?.environment ?? '-'} />
              <HealthMetric label="API 버전" value={health?.api_version ?? '-'} />
              <HealthMetric label="에러율" value={`${errorRatePct}%`} />
              <HealthMetric
                label="메모리"
                value={typeof health?.memory_usage_mb === 'number' ? `${health.memory_usage_mb}MB` : '-'}
              />
            </div>
          )}
          {health && (
            <p className="mt-3 inline-flex items-center gap-1 text-[10px] text-muted-foreground">
              <Activity className="h-3 w-3" />
              요청 {health.request_count.toLocaleString()}회 · 에러 {health.error_count.toLocaleString()}회
            </p>
          )}
        </CardContent>
      </Card>
    </section>
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
                  <li key={report.id}>
                    <Link
                      href={`/?report=${encodeURIComponent(report.id)}`}
                      className="block rounded-sm border border-border px-3 py-2 transition-colors hover:border-primary/40"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{report.title || '제목 없음'}</p>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            {getStyleLabel(report.style)} · {report.time}
                          </p>
                        </div>
                        <span className="signal-meta shrink-0 text-[10px] text-primary">열기</span>
                      </div>
                    </Link>
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

function HealthMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-border bg-background/60 px-3 py-2">
      <p className="signal-meta text-[10px] text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}

'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  BarChart3,
  BookOpen,
  Check,
  Copy,
  FileText,
  Hash,
  RotateCw,
  Server,
  Sparkles,
  Star,
  Zap,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import OperationsDashboard from '@/components/dashboard/OperationsDashboard';
import { MAX_LOCAL_REPORTS, useResultStore } from '@/stores/resultStore';
import { buildLocalDashboardMarkdown, buildLocalDashboardStats, cleanMarkdownLine } from '@/lib/dashboard-summary';
import { getStyleLabel } from '@/lib/helpers';
import { apiUrl } from '@/lib/api';
import { useClipboardCopy } from '@/hooks/useClipboardCopy';
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
  const pinnedIds = useResultStore((s) => s.pinnedIds);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthCheckedAt, setHealthCheckedAt] = useState<Date | null>(null);
  const latestReport = useMemo(
    () =>
      reports.reduce<Report | null>((latest, report) => {
        if (!latest) return report;
        return (report.createdAt ?? 0) > (latest.createdAt ?? 0) ? report : latest;
      }, null),
    [reports]
  );

  const refreshHealth = useCallback(async (signal?: AbortSignal) => {
    setHealthLoading(true);
    try {
      const res = await fetch(apiUrl('/health'), { signal });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
      if (signal?.aborted) return;
      setHealth(data as HealthStatus);
      setHealthError(null);
    } catch (err) {
      if (signal?.aborted) return;
      setHealth(null);
      setHealthError(err instanceof Error ? err.message : 'API 상태를 확인할 수 없습니다.');
    } finally {
      if (signal?.aborted) return;
      setHealthCheckedAt(new Date());
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    hydrateResults();
  }, [hydrateResults]);

  useEffect(() => {
    const controller = new AbortController();
    void refreshHealth(controller.signal);
    return () => controller.abort();
  }, [refreshHealth]);

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
        <DashboardQuickActions latestReport={latestReport} />
        <LocalDashboardSummary reports={reports} pinnedIds={pinnedIds} />
        <SystemHealthCard
          health={health}
          error={healthError}
          isLoading={healthLoading}
          checkedAt={healthCheckedAt}
          onRefresh={() => void refreshHealth()}
        />
        <OperationsDashboard />
      </div>
    </div>
  );
}

function DashboardQuickActions({ latestReport }: { latestReport: Report | null }) {
  return (
    <section className="mb-6 grid gap-3 md:grid-cols-3">
      <QuickActionCard
        href="/"
        icon={<Sparkles className="h-4 w-4" />}
        title="새 콘텐츠 만들기"
        description="URL이나 텍스트로 바로 생성하고 학습 노트로 이어갑니다."
        actionLabel="시작"
      />
      <QuickActionCard
        href="/notes"
        icon={<BookOpen className="h-4 w-4" />}
        title="지식위키 열기"
        description="저장한 노트, 근거, 관련 개념을 다시 탐색합니다."
        actionLabel="열기"
      />
      <QuickActionCard
        href={latestReport ? `/?report=${encodeURIComponent(latestReport.id)}` : '/'}
        icon={<FileText className="h-4 w-4" />}
        title="최근 결과 이어보기"
        description={
          latestReport
            ? cleanMarkdownLine(latestReport.title || latestReport.youtube_title, '최근 생성 결과로 이동합니다.')
            : '생성 결과가 생기면 여기서 바로 이어볼 수 있습니다.'
        }
        actionLabel={latestReport ? '이어보기' : '홈으로'}
      />
    </section>
  );
}

function QuickActionCard({
  href,
  icon,
  title,
  description,
  actionLabel,
}: {
  href: string;
  icon: ReactNode;
  title: string;
  description: string;
  actionLabel: string;
}) {
  return (
    <Link
      href={href}
      className="group rounded-sm border border-border bg-card p-4 shadow-none transition-colors hover:border-primary/40"
    >
      <div className="mb-3 inline-flex h-8 w-8 items-center justify-center rounded-sm bg-primary/10 text-primary">
        {icon}
      </div>
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{description}</p>
      <span className="mt-3 inline-flex items-center gap-1 text-[10px] font-semibold text-primary">
        {actionLabel}
        <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

function SystemHealthCard({
  health,
  error,
  isLoading,
  checkedAt,
  onRefresh,
}: {
  health: HealthStatus | null;
  error: string | null;
  isLoading: boolean;
  checkedAt: Date | null;
  onRefresh: () => void;
}) {
  const { status: copyStatus, copyText } = useClipboardCopy({ resetDelayMs: 1800 });
  const copied = copyStatus === 'copied';
  const statusLabel = health?.status === 'healthy' ? '정상' : error ? '확인 필요' : isLoading ? '확인 중' : '-';
  const errorRatePct = health ? Math.round((health.error_rate ?? 0) * 1000) / 10 : 0;
  const checkedAtLabel = checkedAt
    ? checkedAt.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;

  async function copyDiagnostics() {
    const payload = {
      captured_at: new Date().toISOString(),
      page: 'dashboard',
      api_base: apiUrl('/').replace(/\/$/, ''),
      health: health ?? null,
      health_error: error ?? null,
      health_loading: isLoading,
      health_checked_at: checkedAt?.toISOString() ?? null,
      user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
    };
    const result = await copyText(() => JSON.stringify(payload, null, 2));
    if (!result.isCurrent) return;
    if (result.copied) {
      toast.success('진단 정보가 복사되었습니다.');
    } else {
      toast.error('진단 정보를 복사하지 못했습니다.');
    }
  }

  return (
    <section className="mb-6">
      <Card className="rounded-sm border-border bg-card shadow-none">
        <CardHeader className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
            <Server className="h-4 w-4" /> 시스템 건강도
          </CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 text-xs"
              disabled={isLoading}
              onClick={onRefresh}
            >
              <RotateCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              새로고침
            </Button>
            <Button type="button" variant="outline" size="sm" className="h-8 gap-1.5 text-xs" onClick={copyDiagnostics}>
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              진단 복사
            </Button>
          </div>
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
          <p className="mt-2 text-[10px] text-muted-foreground">
            {isLoading ? '현재 상태를 새로 확인 중입니다.' : checkedAtLabel ? `마지막 확인 ${checkedAtLabel}` : '아직 확인 전입니다.'}
          </p>
        </CardContent>
      </Card>
    </section>
  );
}

function LocalDashboardSummary({ reports, pinnedIds }: { reports: Report[]; pinnedIds: Set<string> }) {
  const { status: summaryCopyStatus, copyText } = useClipboardCopy({ resetDelayMs: 1800 });
  const summaryCopied = summaryCopyStatus === 'copied';
  const stats = useMemo(() => buildLocalDashboardStats(reports, pinnedIds, MAX_LOCAL_REPORTS), [pinnedIds, reports]);

  async function copyMarkdownSummary() {
    const result = await copyText(() =>
      buildLocalDashboardMarkdown(stats, reports.length, MAX_LOCAL_REPORTS),
    );
    if (!result.isCurrent) return;
    if (result.copied) {
      toast.success('작업 요약 Markdown이 복사되었습니다.');
    } else {
      toast.error('작업 요약 Markdown을 복사하지 못했습니다.');
    }
  }

  return (
    <section className="mb-6 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="signal-meta mb-2 text-[10px] font-semibold text-primary">LOCAL ACTIVITY</p>
          <h1 className="text-2xl font-bold tracking-[-0.02em]">내 작업 요약</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            서버 운영 지표와 별개로, 이 브라우저에 저장된 최근 생성 결과를 요약합니다.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" className="h-8 gap-1.5 text-xs" onClick={copyMarkdownSummary}>
          {summaryCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          Markdown 복사
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <LocalMetric icon={<FileText className="h-4 w-4" />} label="저장된 결과" value={`${reports.length}개`} />
        <LocalMetric icon={<BookOpen className="h-4 w-4" />} label="학습 노트 연결" value={`${stats.linkedNoteCount}개`} />
        <LocalMetric icon={<Zap className="h-4 w-4" />} label="누적 토큰" value={stats.totalTokens.toLocaleString()} />
        <LocalMetric icon={<Hash className="h-4 w-4" />} label="평균 길이" value={`${stats.avgLength.toLocaleString()}자`} />
        <LocalMetric icon={<Server className="h-4 w-4" />} label="저장 공간" value={`${reports.length}/${MAX_LOCAL_REPORTS}`} />
      </div>

      <Card className="rounded-sm border-border bg-card shadow-none">
        <CardContent className="px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="signal-meta text-[10px] text-muted-foreground">로컬 저장 공간</p>
              <p className="mt-1 text-sm text-foreground">
                {stats.storageStatus} · {stats.storagePct}% 사용 중
              </p>
            </div>
            <p className="max-w-xl text-xs text-muted-foreground">
              결과는 이 브라우저에 최대 {MAX_LOCAL_REPORTS}개까지 보관됩니다.
              한도를 넘으면 오래된 결과부터 자동으로 밀려납니다.
            </p>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${Math.min(stats.storagePct, 100)}%` }} />
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-sm border-border bg-card shadow-none">
        <CardHeader>
          <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
            <Activity className="h-4 w-4" /> 최근 7일 생성 흐름
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-7 items-end gap-2">
            {stats.activityDays.map((day) => (
              <div key={day.key} className="flex min-w-0 flex-col items-center gap-2">
                <div className="flex h-20 w-full items-end justify-center rounded-sm bg-muted/40 px-1 py-1">
                  <div
                    className={`w-full max-w-8 rounded-sm transition-all ${day.count > 0 ? 'bg-primary' : 'bg-muted'}`}
                    style={{ height: `${day.count > 0 ? Math.max(10, Math.round((day.count / stats.maxActivityCount) * 72)) : 8}px` }}
                    aria-label={`${day.label} 생성 ${day.count}건`}
                  />
                </div>
                <div className="text-center">
                  <p className="signal-meta text-[10px] text-muted-foreground">{day.label}</p>
                  <p className="mt-0.5 text-xs font-semibold">{day.count}건</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-4">
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
              <Star className="h-4 w-4" /> 고정 결과
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.pinned.length === 0 ? (
              <p className="text-sm text-muted-foreground">중요한 결과를 카드에서 고정하면 여기에 모입니다.</p>
            ) : (
              <ul className="space-y-2">
                {stats.pinned.map((report) => (
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

        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <BookOpen className="h-4 w-4" /> 연결된 학습 노트
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.linkedNotes.length === 0 ? (
              <p className="text-sm text-muted-foreground">결과 카드에서 학습 노트로 저장하면 여기에 연결됩니다.</p>
            ) : (
              <ul className="space-y-2">
                {stats.linkedNotes.map((report) => (
                  <li key={report.id}>
                    <Link
                      href={`/notes/${encodeURIComponent(report.knowledge_note_id ?? '')}`}
                      className="block rounded-sm border border-border px-3 py-2 transition-colors hover:border-primary/40"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{report.knowledge_note_title || report.title || '제목 없음'}</p>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            {getStyleLabel(report.style)} · {report.time}
                          </p>
                        </div>
                        <span className="signal-meta shrink-0 text-[10px] text-primary">노트</span>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
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

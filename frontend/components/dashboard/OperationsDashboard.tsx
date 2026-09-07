'use client';
import { memo, useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, Clock, CheckCircle, BarChart3, FileText, Gauge, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import { authFetch } from '@/lib/auth-session';
import { useAuthUserId } from '@/hooks/useAuthUserId';

interface DashboardData {
  total_generations: number;
  success_rate: number;
  avg_time: number;
  style_distribution: Record<string, number>;
  daily_usage: Array<{ date: string; count: number }>;
  avg_content_length?: number;
  top_styles?: Array<{ style: string; count: number }>;
  recent_generations?: Array<{ title: string; style: string; created_at: string }>;
  busiest_hour?: number | null;
  provider_distribution?: Record<string, string>;
}

export const OperationsDashboard = memo(function OperationsDashboard() {
  const authUserId = useAuthUserId();
  return <AccountOperationsDashboard key={`operations:${authUserId ?? 'anonymous'}`} />;
});

function AccountOperationsDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    void (async () => {
      try {
        const response = await authFetch(apiUrl('/api/admin/dashboard'), {
          signal: controller.signal,
        });
        const body = await response.json();
        if (!active || controller.signal.aborted) return;

        if (body.error) {
          setError(body.error);
        } else {
          setData(body as DashboardData);
        }
      } catch {
        if (!active || controller.signal.aborted) return;
        setError('데이터를 가져올 수 없습니다.');
      } finally {
        if (active && !controller.signal.aborted) setLoading(false);
      }
    })();

    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  if (loading) return <div className="signal-meta py-12 text-center text-[10px] text-muted-foreground">로딩 중...</div>;
  if (error) {
    return (
      <Card className="rounded-sm border-border bg-card shadow-none">
        <CardContent className="py-10 text-center">
          <p className="text-sm font-medium text-destructive">{error}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            운영 대시보드는 관리자 권한과 Supabase 연결이 필요합니다.
          </p>
          <Button asChild variant="outline" size="sm" className="mt-4">
            <Link href="/">생성 화면으로 돌아가기</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }
  if (!data) return null;

  const topStyles = data.top_styles?.length
    ? data.top_styles.map((item) => [item.style, item.count] as const)
    : Object.entries(data.style_distribution)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5);
  const providers = Object.entries(data.provider_distribution ?? {});

  return (
    <div className="space-y-6">
      <div>
        <p className="signal-meta mb-2 text-[10px] font-semibold text-primary">OPERATIONS</p>
        <h2 className="text-2xl font-bold tracking-[-0.02em]">운영 대시보드</h2>
        <p className="mt-1 text-sm text-muted-foreground">최근 7일 생성 품질과 처리 흐름을 확인해요.</p>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <Activity className="h-4 w-4" /> 총 생성
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold tracking-[-0.03em]">{data.total_generations}</span>
          </CardContent>
        </Card>
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <CheckCircle className="h-4 w-4" /> 성공률
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold tracking-[-0.03em]">{data.success_rate}%</span>
          </CardContent>
        </Card>
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <Clock className="h-4 w-4" /> 평균 시간
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold tracking-[-0.03em]">{data.avg_time}초</span>
          </CardContent>
        </Card>
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <FileText className="h-4 w-4" /> 평균 길이
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold tracking-[-0.03em]">{(data.avg_content_length ?? 0).toLocaleString()}</span>
          </CardContent>
        </Card>
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader className="pb-2">
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <Gauge className="h-4 w-4" /> 피크 시간
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-3xl font-bold tracking-[-0.03em]">
              {data.busiest_hour === null || data.busiest_hour === undefined ? '-' : `${data.busiest_hour}시`}
            </span>
          </CardContent>
        </Card>
      </div>

      {/* 스타일 분포 */}
      <Card className="rounded-sm border-border bg-card shadow-none">
        <CardHeader>
          <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
            <BarChart3 className="h-4 w-4" /> 스타일 분포 (TOP 5)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {topStyles.map(([style, count]) => {
              const pct = data.total_generations > 0 ? Math.round((count / data.total_generations) * 100) : 0;
              return (
                <div key={style} className="flex items-center gap-3">
                  <span className="text-sm w-24 truncate">{style}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="signal-meta w-12 text-right text-[10px] text-muted-foreground">{count}건</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <FileText className="h-4 w-4" /> 최근 생성
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(data.recent_generations ?? []).length === 0 ? (
              <p className="text-sm text-muted-foreground">최근 생성 기록이 없습니다.</p>
            ) : (
              <ul className="space-y-2">
                {(data.recent_generations ?? []).map((item, idx) => (
                  <li key={`${item.created_at}-${idx}`} className="rounded-sm border border-border px-3 py-2">
                    <p className="truncate text-sm font-medium">{item.title}</p>
                    <p className="mt-1 text-[10px] text-muted-foreground">{item.style} · {item.created_at || '시간 없음'}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="signal-meta flex items-center gap-2 text-[10px] text-muted-foreground">
              <Server className="h-4 w-4" /> 프로바이더 상태
            </CardTitle>
          </CardHeader>
          <CardContent>
            {providers.length === 0 ? (
              <p className="text-sm text-muted-foreground">활성 프로바이더 정보가 없습니다.</p>
            ) : (
              <div className="space-y-2">
                {providers.map(([name, status]) => (
                  <div key={name} className="flex items-center justify-between rounded-sm border border-border px-3 py-2">
                    <span className="text-sm font-medium">{name}</span>
                    <span className="signal-meta text-[10px] text-primary">{status}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 일별 사용량 */}
      {data.daily_usage.length > 0 && (
        <Card className="rounded-sm border-border bg-card shadow-none">
          <CardHeader>
            <CardTitle className="signal-meta text-[10px] text-muted-foreground">일별 사용량</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1 h-24">
              {data.daily_usage.slice(0, 7).reverse().map((d) => {
                const max = Math.max(...data.daily_usage.map(u => u.count), 1);
                const height = Math.max(4, (d.count / max) * 100);
                return (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full rounded-t-sm bg-primary"
                      style={{ height: `${height}%` }}
                      title={`${d.date}: ${d.count}건`}
                    />
                    <span className="signal-meta text-[9px] text-muted-foreground">{d.date.slice(5)}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default OperationsDashboard;

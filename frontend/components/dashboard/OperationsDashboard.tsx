'use client';
import { memo, useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, Clock, CheckCircle, BarChart3 } from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface DashboardData {
  total_generations: number;
  success_rate: number;
  avg_time: number;
  style_distribution: Record<string, number>;
  daily_usage: Array<{ date: string; count: number }>;
}

export const OperationsDashboard = memo(function OperationsDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(apiUrl('/api/admin/dashboard'))
      .then(r => r.json())
      .then(d => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => setError('데이터를 가져올 수 없습니다.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="signal-meta py-12 text-center text-[10px] text-muted-foreground">로딩 중...</div>;
  if (error) return <div className="py-12 text-center text-sm text-destructive">{error}</div>;
  if (!data) return null;

  const topStyles = Object.entries(data.style_distribution)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <p className="signal-meta mb-2 text-[10px] font-semibold text-primary">OPERATIONS</p>
        <h2 className="text-2xl font-bold tracking-[-0.02em]">운영 대시보드</h2>
        <p className="mt-1 text-sm text-muted-foreground">최근 7일 생성 품질과 처리 흐름을 확인해요.</p>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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
});

export default OperationsDashboard;

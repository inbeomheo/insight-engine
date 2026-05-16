'use client';
import { memo, useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Activity, Clock, CheckCircle, BarChart3 } from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { fetchWithAuth } from '@/lib/auth';

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
    fetchWithAuth(apiUrl('/api/admin/dashboard'))
      .then(r => r.json())
      .then(d => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => setError('데이터를 가져올 수 없습니다.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12 text-zinc-500">로딩 중...</div>;
  if (error) return <div className="text-center py-12 text-red-500">{error}</div>;
  if (!data) return null;

  const topStyles = Object.entries(data.style_distribution)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">운영 대시보드 (최근 7일)</h2>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-500 flex items-center gap-2">
              <Activity className="h-4 w-4" /> 총 생성
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">{data.total_generations}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-500 flex items-center gap-2">
              <CheckCircle className="h-4 w-4" /> 성공률
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">{data.success_rate}%</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-500 flex items-center gap-2">
              <Clock className="h-4 w-4" /> 평균 시간
            </CardTitle>
          </CardHeader>
          <CardContent>
            <span className="text-2xl font-bold">{data.avg_time}초</span>
          </CardContent>
        </Card>
      </div>

      {/* 스타일 분포 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
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
                  <div className="flex-1 h-2 bg-zinc-200 dark:bg-zinc-700 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-zinc-500 w-12 text-right">{count}건</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 일별 사용량 */}
      {data.daily_usage.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">일별 사용량</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-1 h-24">
              {data.daily_usage.slice(0, 7).reverse().map((d) => {
                const max = Math.max(...data.daily_usage.map(u => u.count), 1);
                const height = Math.max(4, (d.count / max) * 100);
                return (
                  <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full bg-blue-500 rounded-t"
                      style={{ height: `${height}%` }}
                      title={`${d.date}: ${d.count}건`}
                    />
                    <span className="text-[10px] text-zinc-500 dark:text-zinc-400">{d.date.slice(5)}</span>
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

'use client';

import { memo, useEffect, useState } from 'react';
import { BarChart3, Coins, Calendar } from 'lucide-react';

interface UsageData {
  credits: { balance: number; plan: string };
  usage: { usage_count: number; max_usage: number; can_use: boolean };
  subscription: { plan: string; status: string };
  daily_usage: Array<{ date: string; used_count: number }>;
}

export const UsageDashboard = memo(function UsageDashboard() {
  const [data, setData] = useState<UsageData | null>(null);

  useEffect(() => {
    fetch('/api/usage/my-usage')
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, []);

  if (!data) {
    return <div className="p-4 text-center text-muted-foreground">사용량 정보를 불러오는 중...</div>;
  }

  const { credits, usage, subscription, daily_usage } = data;
  const maxBar = Math.max(...daily_usage.map((d) => d.used_count), 1);

  return (
    <div className="space-y-6 p-4">
      {/* 요약 카드 */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          icon={<Coins className="h-5 w-5 text-amber-500" />}
          label="크레딧 잔액"
          value={credits.balance}
        />
        <StatCard
          icon={<BarChart3 className="h-5 w-5 text-blue-500" />}
          label="오늘 사용량"
          value={`${usage.max_usage - usage.usage_count} / ${usage.max_usage}`}
        />
        <StatCard
          icon={<Calendar className="h-5 w-5 text-green-500" />}
          label="현재 플랜"
          value={subscription.plan.toUpperCase()}
        />
      </div>

      {/* 일별 사용량 차트 (간단 바 차트) */}
      {daily_usage.length > 0 && (
        <div className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold mb-3">최근 7일 사용량</h3>
          <div className="flex items-end gap-1 h-24">
            {daily_usage.map((d) => (
              <div key={d.date} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className="w-full bg-primary/80 rounded-t transition-all"
                  style={{ height: `${(d.used_count / maxBar) * 100}%`, minHeight: d.used_count > 0 ? 4 : 0 }}
                />
                <span className="text-[10px] text-muted-foreground">
                  {d.date.slice(5)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border p-3 flex items-center gap-3">
      {icon}
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-lg font-bold">{value}</p>
      </div>
    </div>
  );
}

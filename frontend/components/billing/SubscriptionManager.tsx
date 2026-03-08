'use client';

import { memo, useEffect, useState } from 'react';
import { CreditCard, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { apiUrl } from '@/lib/api';

interface SubscriptionInfo {
  plan: string;
  status: string;
  stripe_subscription_id?: string;
  activated_at?: string;
  canceled_at?: string;
}

export const SubscriptionManager = memo(function SubscriptionManager() {
  const [sub, setSub] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchSub = () => {
    fetch(apiUrl('/api/subscription'))
      .then((r) => (r.ok ? r.json() : null))
      .then(setSub)
      .catch(() => {});
  };

  useEffect(fetchSub, []);

  const handleCancel = async () => {
    if (!confirm('구독을 취소하시겠습니까? Free 플랜으로 전환됩니다.')) return;
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/api/subscription/cancel'), { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        toast.success('구독이 취소되었습니다.');
        fetchSub();
      } else {
        toast.error(data.error || '취소 실패');
      }
    } catch {
      toast.error('요청 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  if (!sub) return null;

  const statusLabels: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' }> = {
    active: { label: '활성', variant: 'default' },
    canceled: { label: '취소됨', variant: 'destructive' },
    trialing: { label: '체험 중', variant: 'secondary' },
  };

  const st = statusLabels[sub.status] ?? { label: sub.status, variant: 'secondary' as const };

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">구독 관리</h3>
        </div>
        <Badge variant={st.variant}>{st.label}</Badge>
      </div>

      <div className="text-sm text-muted-foreground">
        <p>현재 플랜: <strong className="text-foreground">{sub.plan.toUpperCase()}</strong></p>
        {sub.activated_at && (
          <p>시작일: {new Date(sub.activated_at).toLocaleDateString('ko-KR')}</p>
        )}
      </div>

      {sub.plan !== 'free' && sub.status === 'active' && (
        <div className="flex items-center gap-2 pt-2">
          <Button variant="destructive" size="sm" onClick={handleCancel} disabled={loading}>
            <AlertTriangle className="h-3 w-3 mr-1" />
            {loading ? '처리 중...' : '구독 취소'}
          </Button>
        </div>
      )}
    </div>
  );
});

'use client';

import { memo, useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { apiUrl } from '@/lib/api';

interface PlanInfo {
  name: string;
  credits_per_day: number;
  price_monthly: number;
  price_yearly: number;
  features: string[];
}

export const PricingPage = memo(function PricingPage() {
  const [plans, setPlans] = useState<Record<string, PlanInfo>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(apiUrl('/api/credits/plans'))
      .then((r) => r.json())
      .then((d) => setPlans(d.plans ?? {}))
      .catch(() => toast.error('플랜 정보를 불러오지 못했습니다.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6 text-center text-muted-foreground">로딩 중...</div>;

  const planOrder = ['free', 'pro', 'team'];

  return (
    <div className="grid gap-6 md:grid-cols-3 p-6">
      {planOrder.map((id) => {
        const plan = plans[id];
        if (!plan) return null;
        const isPro = id === 'pro';

        return (
          <div
            key={id}
            className={`rounded-xl border p-6 flex flex-col ${
              isPro ? 'border-primary ring-2 ring-primary/20' : ''
            }`}
          >
            {isPro && (
              <span className="text-xs font-semibold text-primary mb-2">인기</span>
            )}
            <h3 className="text-xl font-bold">{plan.name}</h3>
            <p className="text-3xl font-bold mt-2">
              {plan.price_monthly === 0
                ? '무료'
                : `₩${plan.price_monthly.toLocaleString()}`}
              {plan.price_monthly > 0 && (
                <span className="text-sm font-normal text-muted-foreground">/월</span>
              )}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              일 {plan.credits_per_day}회 생성
            </p>

            <ul className="mt-6 space-y-2 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>

            <CheckoutButton planId={id} planName={plan.name} disabled={id === 'free'} />
          </div>
        );
      })}
    </div>
  );
});

function CheckoutButton({
  planId,
  planName,
  disabled,
}: {
  planId: string;
  planName: string;
  disabled: boolean;
}) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (disabled) return;
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/api/payment/checkout'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price_id: planId, mode: 'subscription' }),
      });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      } else {
        toast.error(data.error || '결제 세션 생성 실패');
      }
    } catch {
      toast.error('결제 요청 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      className="mt-4 w-full"
      variant={disabled ? 'outline' : 'default'}
      disabled={disabled || loading}
      onClick={handleClick}
    >
      {disabled ? '현재 플랜' : loading ? '처리 중...' : `${planName} 시작하기`}
    </Button>
  );
}

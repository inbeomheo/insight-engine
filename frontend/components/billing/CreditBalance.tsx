'use client';

import { memo, useEffect, useState } from 'react';
import { Coins, TrendingUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { apiUrl } from '@/lib/api';

interface CreditInfo {
  balance: number;
  plan: string;
  updated_at: string;
}

export const CreditBalance = memo(function CreditBalance() {
  const [credits, setCredits] = useState<CreditInfo | null>(null);

  useEffect(() => {
    fetch(apiUrl('/api/credits/balance'))
      .then((r) => (r.ok ? r.json() : null))
      .then(setCredits)
      .catch(() => {});
  }, []);

  if (!credits) return null;

  const planLabel: Record<string, string> = {
    free: 'Free',
    pro: 'Pro',
    team: 'Team',
  };

  return (
    <div className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm bg-card">
      <Coins className="h-4 w-4 text-amber-500" />
      <span className="font-medium">{credits.balance}</span>
      <span className="text-muted-foreground">크레딧</span>
      <Badge variant="secondary" className="ml-1 text-xs">
        {planLabel[credits.plan] ?? credits.plan}
      </Badge>
    </div>
  );
});

'use client';

import { useState, useCallback } from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { apiUrl } from '@/lib/api';

interface FactClaim {
  claim: string;
  category: string;
  verifiable: boolean;
  confidence: number;
  reasoning: string;
}

interface FactCheckResult {
  claims: FactClaim[];
  summary: {
    total: number;
    verified: number;
    uncertain: number;
    suspicious: number;
  };
}

interface FactCheckBadgeProps {
  content: string;
}

export default function FactCheckBadge({ content }: FactCheckBadgeProps) {
  const [result, setResult] = useState<FactCheckResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runCheck = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/api/fact-check'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      if (res.ok) {
        setResult(await res.json());
      }
    } catch {
      // 실패 시 무시
    } finally {
      setLoading(false);
    }
  }, [content, loading]);

  if (!result) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className="text-[10px] px-1.5 py-0 cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={runCheck}
          >
            {loading ? (
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            ) : (
              <ShieldCheck className="h-3 w-3 mr-1" />
            )}
            팩트체크
          </Badge>
        </TooltipTrigger>
        <TooltipContent>클릭하여 팩트체크 실행</TooltipContent>
      </Tooltip>
    );
  }

  const { summary } = result;
  const allGood = summary.suspicious === 0 && summary.uncertain === 0;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={`text-[10px] px-1.5 py-0 cursor-default ${
            allGood
              ? 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400'
              : summary.suspicious > 0
                ? 'border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400'
                : 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400'
          }`}
        >
          {allGood ? (
            <ShieldCheck className="h-3 w-3 mr-1" />
          ) : summary.suspicious > 0 ? (
            <ShieldAlert className="h-3 w-3 mr-1" />
          ) : (
            <AlertTriangle className="h-3 w-3 mr-1" />
          )}
          {summary.verified}/{summary.total}
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-sm">
        <div className="space-y-1.5 text-xs">
          <div className="font-medium">
            팩트체크: {summary.verified}건 확인 / {summary.uncertain}건 불확실 / {summary.suspicious}건 의심
          </div>
          {result.claims.slice(0, 5).map((c, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <span className={
                c.confidence >= 0.7 ? 'text-green-500' :
                c.confidence >= 0.3 ? 'text-yellow-500' : 'text-red-500'
              }>
                {c.confidence >= 0.7 ? 'V' : c.confidence >= 0.3 ? '?' : '!'}
              </span>
              <span className="line-clamp-2">{c.claim}</span>
            </div>
          ))}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

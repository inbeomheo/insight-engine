'use client';

import { useState, useCallback } from 'react';
import { ShieldCheck, ShieldAlert, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { qaCheck } from '@/lib/api';
import type { QaCheckResponse } from '@/lib/types';

interface QaGateBadgeProps {
  content: string;
}

export default function QaGateBadge({ content }: QaGateBadgeProps) {
  const [result, setResult] = useState<QaCheckResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const runCheck = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await qaCheck(content);
      setResult(res);
    } catch {
      // 실패 시 무시 — 배지를 표시하지 않음
    } finally {
      setLoading(false);
    }
  }, [content, loading]);

  // 아직 검증 안 했으면 클릭 가능한 뱃지
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
            QA
          </Badge>
        </TooltipTrigger>
        <TooltipContent>클릭하여 품질 검증 실행</TooltipContent>
      </Tooltip>
    );
  }

  // 결과 뱃지
  const passed = result.passed;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={`text-[10px] px-1.5 py-0 cursor-default ${
            passed
              ? 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400'
              : 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400'
          }`}
        >
          {passed ? (
            <ShieldCheck className="h-3 w-3 mr-1" />
          ) : (
            <ShieldAlert className="h-3 w-3 mr-1" />
          )}
          QA {result.score}
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs">
        <div className="space-y-1 text-xs">
          <div className="font-medium mb-1">
            {passed ? 'QA 통과' : 'QA 미통과'} (점수: {result.score}/100)
          </div>
          {result.issues.length === 0 ? (
            <p className="text-muted-foreground">이슈 없음</p>
          ) : (
            <ul className="space-y-0.5">
              {result.issues.map((issue, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className={issue.severity === 'error' ? 'text-red-500' : 'text-yellow-500'}>
                    {issue.severity === 'error' ? '!!' : '!'}
                  </span>
                  <span>{issue.message}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

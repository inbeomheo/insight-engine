'use client';

import { useState, useCallback } from 'react';
import { Copy, Loader2, CheckCircle2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface PlagiarismResult {
  score: number;
  duplicate_ratio: number;
  repeated_phrases: { phrase: string; count: number }[];
  similar_sentences: { sentence_a: string; sentence_b: string; similarity: number }[];
  verdict: 'clean' | 'minor' | 'significant';
}

interface PlagiarismScoreProps {
  content: string;
}

const VERDICT_LABELS: Record<string, string> = {
  clean: '중복 없음',
  minor: '경미한 중복',
  significant: '상당한 중복',
};

export default function PlagiarismScore({ content }: PlagiarismScoreProps) {
  const [result, setResult] = useState<PlagiarismResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runCheck = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch('/api/plagiarism-check', {
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
              <Copy className="h-3 w-3 mr-1" />
            )}
            중복검사
          </Badge>
        </TooltipTrigger>
        <TooltipContent>클릭하여 중복/표절 검사</TooltipContent>
      </Tooltip>
    );
  }

  const isClean = result.verdict === 'clean';

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={`text-[10px] px-1.5 py-0 cursor-default ${
            isClean
              ? 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400'
              : result.verdict === 'minor'
                ? 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400'
                : 'border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400'
          }`}
        >
          {isClean ? (
            <CheckCircle2 className="h-3 w-3 mr-1" />
          ) : (
            <Copy className="h-3 w-3 mr-1" />
          )}
          {VERDICT_LABELS[result.verdict]}
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-sm">
        <div className="space-y-1.5 text-xs">
          <div className="font-medium">
            중복 점수: {result.score}/100 ({(result.duplicate_ratio * 100).toFixed(1)}% 반복)
          </div>
          {result.repeated_phrases.length > 0 && (
            <div>
              <span className="text-muted-foreground">반복 구문:</span>
              {result.repeated_phrases.slice(0, 3).map((p, i) => (
                <div key={i} className="ml-2 truncate">
                  &quot;{p.phrase}&quot; x{p.count}
                </div>
              ))}
            </div>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

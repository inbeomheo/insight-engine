'use client';

import { useState, useCallback } from 'react';
import { BookOpen, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface ReadabilityResult {
  score: number;
  grade: 'A' | 'B' | 'C' | 'D';
  details: {
    avg_sentence_length: number;
    vocabulary_diversity: number;
    foreign_ratio: number;
    paragraph_count: number;
    sentence_count: number;
    char_count: number;
  };
  suggestions: string[];
}

interface ReadabilityGaugeProps {
  content: string;
}

const GRADE_COLORS: Record<string, string> = {
  A: 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400',
  B: 'border-blue-500/50 text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400',
  C: 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400',
  D: 'border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400',
};

export default function ReadabilityGauge({ content }: ReadabilityGaugeProps) {
  const [result, setResult] = useState<ReadabilityResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runCheck = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch('/api/readability', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: content }),
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
              <BookOpen className="h-3 w-3 mr-1" />
            )}
            가독성
          </Badge>
        </TooltipTrigger>
        <TooltipContent>클릭하여 가독성 분석</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={`text-[10px] px-1.5 py-0 cursor-default ${GRADE_COLORS[result.grade] || ''}`}
        >
          <BookOpen className="h-3 w-3 mr-1" />
          {result.grade} ({result.score})
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs">
        <div className="space-y-1 text-xs">
          <div className="font-medium">가독성 {result.grade}등급 ({result.score}/100)</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-muted-foreground">
            <span>평균 문장 길이</span>
            <span>{result.details.avg_sentence_length}자</span>
            <span>어휘 다양성</span>
            <span>{(result.details.vocabulary_diversity * 100).toFixed(0)}%</span>
            <span>외래어 비율</span>
            <span>{(result.details.foreign_ratio * 100).toFixed(1)}%</span>
            <span>문단 수</span>
            <span>{result.details.paragraph_count}개</span>
          </div>
          {result.suggestions.length > 0 && (
            <ul className="space-y-0.5 mt-1">
              {result.suggestions.map((s, i) => (
                <li key={i} className="text-muted-foreground">{s}</li>
              ))}
            </ul>
          )}
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

'use client';

import { useState, useCallback } from 'react';
import { BarChart3, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

interface ScoreResult {
  total_score: number;
  seo: number;
  readability: number;
  originality: number;
  structure: number;
  details: Record<string, number | string>;
}

interface ScoreCardProps {
  content: string;
}

const SCORE_LABELS: Record<string, string> = {
  seo: 'SEO',
  readability: '가독성',
  originality: '독창성',
  structure: '구조',
};

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600 dark:text-green-400';
  if (score >= 60) return 'text-blue-600 dark:text-blue-400';
  if (score >= 40) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function getProgressColor(score: number): string {
  if (score >= 80) return '[&>div]:bg-green-500';
  if (score >= 60) return '[&>div]:bg-blue-500';
  if (score >= 40) return '[&>div]:bg-yellow-500';
  return '[&>div]:bg-red-500';
}

export default function ScoreCard({ content }: ScoreCardProps) {
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [loading, setLoading] = useState(false);

  const analyze = useCallback(async () => {
    if (loading || !content) return;
    setLoading(true);
    try {
      const res = await fetch('/api/content-score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error('점수 분석 실패');
      const data: ScoreResult = await res.json();
      setResult(data);
    } catch {
      // 실패 시 무시
    } finally {
      setLoading(false);
    }
  }, [content, loading]);

  if (!result) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="h-7 text-xs gap-1"
        onClick={analyze}
        disabled={loading}
      >
        {loading ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <BarChart3 className="h-3 w-3" />
        )}
        점수 분석
      </Button>
    );
  }

  return (
    <div className="rounded-lg border p-3 space-y-3 bg-card">
      {/* 종합 점수 */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">종합 점수</span>
        <span className={`text-2xl font-bold ${getScoreColor(result.total_score)}`}>
          {result.total_score}
        </span>
      </div>

      {/* 항목별 프로그레스 바 */}
      <div className="space-y-2">
        {(['seo', 'readability', 'originality', 'structure'] as const).map((key) => {
          const score = result[key];
          return (
            <div key={key} className="space-y-0.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{SCORE_LABELS[key]}</span>
                <span className={getScoreColor(score)}>{score}</span>
              </div>
              <Progress
                value={score}
                className={`h-1.5 ${getProgressColor(score)}`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

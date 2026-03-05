'use client';

import { useState, useCallback } from 'react';
import { Activity, Loader2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface FlowItem {
  paragraph_index: number;
  text_preview: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  score: number;
  emotion: string;
}

interface SentimentFlowResult {
  flow: FlowItem[];
  overall_arc: 'ascending' | 'descending' | 'stable' | 'fluctuating';
  dominant_emotion: string;
}

interface SentimentFlowProps {
  content: string;
}

const ARC_LABELS: Record<string, string> = {
  ascending: '상승',
  descending: '하강',
  stable: '안정',
  fluctuating: '변동',
};

const SENTIMENT_COLORS: Record<string, string> = {
  positive: 'bg-green-400',
  neutral: 'bg-gray-400',
  negative: 'bg-red-400',
};

export default function SentimentFlow({ content }: SentimentFlowProps) {
  const [result, setResult] = useState<SentimentFlowResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runAnalysis = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch('/api/sentiment-flow', {
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
            onClick={runAnalysis}
          >
            {loading ? (
              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
            ) : (
              <Activity className="h-3 w-3 mr-1" />
            )}
            감정흐름
          </Badge>
        </TooltipTrigger>
        <TooltipContent>클릭하여 감정 흐름 분석</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className="text-[10px] px-1.5 py-0 cursor-default"
        >
          <Activity className="h-3 w-3 mr-1" />
          {ARC_LABELS[result.overall_arc] || result.overall_arc} · {result.dominant_emotion}
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-sm">
        <div className="space-y-2 text-xs">
          <div className="font-medium">
            감정 흐름: {ARC_LABELS[result.overall_arc]} / 주요 감정: {result.dominant_emotion}
          </div>
          {/* 미니 바 차트 */}
          <div className="flex items-end gap-0.5 h-8">
            {result.flow.map((item, i) => {
              const height = Math.max(10, Math.abs(item.score) * 100);
              return (
                <div
                  key={i}
                  className={`w-2 rounded-sm ${SENTIMENT_COLORS[item.sentiment]}`}
                  style={{ height: `${height}%`, opacity: 0.5 + Math.abs(item.score) * 0.5 }}
                  title={`${item.emotion}: ${item.score.toFixed(2)}`}
                />
              );
            })}
          </div>
          {/* 범례 */}
          <div className="flex gap-3 text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-400" />긍정
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-gray-400" />중립
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-400" />부정
            </span>
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

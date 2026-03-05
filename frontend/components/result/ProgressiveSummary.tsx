'use client';

import { useState, useCallback } from 'react';
import { FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface SummaryResult {
  one_line: string;
  three_lines: string;
  full_summary: string;
}

interface ProgressiveSummaryProps {
  content: string;
  model?: string;
}

export default function ProgressiveSummary({ content, model }: ProgressiveSummaryProps) {
  const [result, setResult] = useState<SummaryResult | null>(null);
  const [loading, setLoading] = useState(false);

  const generateSummary = useCallback(async () => {
    if (loading || !content) return;
    setLoading(true);
    try {
      const res = await fetch('/api/progressive-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, model }),
      });
      if (!res.ok) throw new Error('요약 생성 실패');
      const data: SummaryResult = await res.json();
      setResult(data);
    } catch {
      // 실패 시 무시
    } finally {
      setLoading(false);
    }
  }, [content, model, loading]);

  if (!result) {
    return (
      <Button
        variant="ghost"
        size="sm"
        className="h-7 text-xs gap-1"
        onClick={generateSummary}
        disabled={loading}
      >
        {loading ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <FileText className="h-3 w-3" />
        )}
        요약 보기
      </Button>
    );
  }

  return (
    <div className="rounded-lg border p-3 bg-card">
      <Tabs defaultValue="one" className="w-full">
        <TabsList className="h-7 mb-2">
          <TabsTrigger value="one" className="text-xs h-6 px-2">
            1줄
          </TabsTrigger>
          <TabsTrigger value="three" className="text-xs h-6 px-2">
            3줄
          </TabsTrigger>
          <TabsTrigger value="full" className="text-xs h-6 px-2">
            전체
          </TabsTrigger>
        </TabsList>

        <TabsContent value="one" className="mt-0">
          <p className="text-sm leading-relaxed">{result.one_line}</p>
        </TabsContent>

        <TabsContent value="three" className="mt-0">
          <p className="text-sm leading-relaxed whitespace-pre-line">
            {result.three_lines}
          </p>
        </TabsContent>

        <TabsContent value="full" className="mt-0">
          <p className="text-sm leading-relaxed whitespace-pre-line">
            {result.full_summary}
          </p>
        </TabsContent>
      </Tabs>
    </div>
  );
}

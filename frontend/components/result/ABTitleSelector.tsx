'use client';

import { useState, useCallback } from 'react';
import { Copy, Check, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { apiUrl } from '@/lib/api';

interface ABTitleSelectorProps {
  originalTitle: string;
  content: string;
}

/** A/B 테스트 제목 후보 선택 UI */
export default function ABTitleSelector({ originalTitle, content }: ABTitleSelectorProps) {
  const [variants, setVariants] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/api/ab-titles'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: originalTitle, content: content.slice(0, 500) }),
      });
      if (!res.ok) throw new Error('생성 실패');
      const data = await res.json();
      setVariants(data.titles || []);
    } catch {
      toast.error('제목 변형 생성에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  }, [originalTitle, content]);

  const handleCopy = useCallback(async (title: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(title);
      setCopiedIdx(idx);
      toast.success('제목이 복사되었습니다.');
      setTimeout(() => setCopiedIdx(null), 2000);
    } catch {
      toast.error('복사에 실패했습니다.');
    }
  }, []);

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={handleGenerate}
          disabled={loading}
          className="gap-1.5"
        >
          {loading ? (
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" />
          )}
          {variants.length > 0 ? '다시 생성' : 'A/B 제목 생성'}
        </Button>
      </div>

      {variants.length > 0 && (
        <div className="grid gap-1.5">
          {variants.map((title, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 rounded-lg border border-border/50 px-3 py-2 text-sm hover:bg-muted/30 transition-colors"
            >
              <span className="text-muted-foreground text-xs font-mono w-4 shrink-0">
                {idx + 1}
              </span>
              <span className="flex-1">{title}</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 shrink-0"
                onClick={() => handleCopy(title, idx)}
              >
                {copiedIdx === idx ? (
                  <Check className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

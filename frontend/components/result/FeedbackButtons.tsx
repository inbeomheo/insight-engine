'use client';

import { useState, useCallback } from 'react';
import { ThumbsUp, ThumbsDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { apiUrl } from '@/lib/api';

interface FeedbackButtonsProps {
  styleId: string;
  contentId: string;
}

export default function FeedbackButtons({ styleId, contentId }: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState<'like' | 'dislike' | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = useCallback(async (rating: 'like' | 'dislike') => {
    if (loading || submitted) return;
    setLoading(true);
    try {
      const res = await fetch(apiUrl('/api/feedback'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ style_id: styleId, content_id: contentId, rating }),
      });
      if (res.ok) {
        setSubmitted(rating);
      }
    } catch {
      // 실패 시 무시
    } finally {
      setLoading(false);
    }
  }, [styleId, contentId, loading, submitted]);

  if (submitted) {
    return (
      <div className="inline-flex items-center gap-1 text-xs text-muted-foreground">
        {submitted === 'like' ? (
          <ThumbsUp className="h-3.5 w-3.5 text-green-500" />
        ) : (
          <ThumbsDown className="h-3.5 w-3.5 text-red-400" />
        )}
        <span>피드백 완료</span>
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-0.5">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => submit('like')}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <ThumbsUp className="h-3.5 w-3.5" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>도움이 됐어요</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => submit('dislike')}
            disabled={loading}
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>개선이 필요해요</TooltipContent>
      </Tooltip>
    </div>
  );
}

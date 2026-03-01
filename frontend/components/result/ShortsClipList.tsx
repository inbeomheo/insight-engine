'use client';

import { useState } from 'react';
import { Copy, Check, Film, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import type { ShortsClip } from '@/lib/types';

interface ShortsClipListProps {
  clips: ShortsClip[];
}

export default function ShortsClipList({ clips }: ShortsClipListProps) {
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  async function copyScript(script: string, idx: number) {
    await navigator.clipboard.writeText(script);
    setCopiedIdx(idx);
    toast.success('스크립트 복사 완료');
    setTimeout(() => setCopiedIdx(null), 2000);
  }

  if (!clips || clips.length === 0) return null;

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-center gap-1.5 text-xs font-semibold">
        <Film className="h-3.5 w-3.5 text-primary" />
        Shorts 클립 ({clips.length}개)
      </div>

      {clips.map((clip, idx) => (
        <div
          key={idx}
          className="p-3 border border-border rounded-lg bg-muted/50 space-y-2"
        >
          {/* 클립 헤더 */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">{clip.title}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => copyScript(clip.script, idx)}
            >
              {copiedIdx === idx ? (
                <Check className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>

          {/* 후킹 문구 */}
          <blockquote className="border-l-2 border-primary/50 pl-2 text-xs text-primary italic">
            {clip.hook_text}
          </blockquote>

          {/* 타임스탬프 */}
          {(clip.timestamp_start || clip.timestamp_end) && (
            <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Clock className="h-3 w-3" />
              {clip.timestamp_start}
              {clip.timestamp_end && ` ~ ${clip.timestamp_end}`}
              {clip.duration_seconds != null && ` (${clip.duration_seconds}초)`}
            </div>
          )}

          {/* 스크립트 */}
          <p className="text-xs leading-relaxed whitespace-pre-line">
            {clip.script}
          </p>
        </div>
      ))}
    </div>
  );
}

'use client';

import { useMemo } from 'react';
import AudioPlayer from './AudioPlayer';

interface PodcastPlayerProps {
  audioBase64: string;
  script: string;
  title?: string;
  durationEstimate?: number;
  onClose?: () => void;
}

export default function PodcastPlayer({
  audioBase64,
  script,
  title,
  durationEstimate,
  onClose,
}: PodcastPlayerProps) {
  const audioBlob = useMemo(() => {
    const binary = atob(audioBase64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new Blob([bytes], { type: 'audio/mpeg' });
  }, [audioBase64]);

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-foreground/80">
          팟캐스트 에피소드
        </h4>
        {durationEstimate && (
          <span className="text-xs text-muted-foreground">
            약 {Math.ceil(durationEstimate / 60)}분
          </span>
        )}
      </div>

      <AudioPlayer audioBlob={audioBlob} title={title} onClose={onClose} />

      {/* 스크립트 미리보기 */}
      {script && (
        <details className="rounded-lg border border-border/50 bg-muted/20">
          <summary className="cursor-pointer px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
            대화 스크립트 보기
          </summary>
          <div className="px-4 pb-3 pt-1 text-sm leading-relaxed whitespace-pre-wrap text-foreground/80">
            {script}
          </div>
        </details>
      )}
    </div>
  );
}

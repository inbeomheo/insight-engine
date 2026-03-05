'use client';

import { useState } from 'react';
import { Download, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Clip {
  index: number;
  video_base64: string;
  start: string;
  end: string;
}

interface VideoClipPlayerProps {
  clips: Clip[];
}

export default function VideoClipPlayer({ clips }: VideoClipPlayerProps) {
  const [activeClip, setActiveClip] = useState(0);

  if (!clips || clips.length === 0) return null;

  const current = clips[activeClip];
  const videoSrc = `data:video/mp4;base64,${current.video_base64}`;

  function handleDownload(clip: Clip) {
    const a = document.createElement('a');
    a.href = `data:video/mp4;base64,${clip.video_base64}`;
    a.download = `clip_${clip.index + 1}_${clip.start}-${clip.end}.mp4`;
    a.click();
  }

  return (
    <div className="mt-4 space-y-3">
      <h4 className="text-sm font-semibold text-foreground/80">Shorts 클립</h4>

      {/* 비디오 플레이어 */}
      <div className="rounded-lg overflow-hidden border border-border/50 bg-black">
        <video
          key={activeClip}
          src={videoSrc}
          controls
          className="w-full max-h-[400px]"
        />
      </div>

      {/* 클립 목록 */}
      <div className="flex flex-wrap gap-2">
        {clips.map((clip, i) => (
          <div key={clip.index} className="flex items-center gap-1">
            <Button
              variant={i === activeClip ? 'default' : 'outline'}
              size="sm"
              className="gap-1 text-xs"
              onClick={() => setActiveClip(i)}
            >
              <Play className="h-3 w-3" />
              {clip.start} - {clip.end}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => handleDownload(clip)}
              title="다운로드"
            >
              <Download className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

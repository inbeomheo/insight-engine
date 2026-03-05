'use client';

import { useState, useCallback } from 'react';
import { Maximize2, Minimize2, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SlidePreviewProps {
  /** Reveal.js HTML 문자열 */
  html: string;
  title?: string;
}

/** 슬라이드 HTML을 iframe으로 미리보기합니다. */
export default function SlidePreview({ html, title = '슬라이드' }: SlidePreviewProps) {
  const [fullscreen, setFullscreen] = useState(false);

  const blobUrl = URL.createObjectURL(new Blob([html], { type: 'text/html' }));

  const handleDownload = useCallback(() => {
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `${title.slice(0, 50)}.html`;
    a.click();
  }, [blobUrl, title]);

  const toggleFullscreen = useCallback(() => {
    setFullscreen((prev) => !prev);
  }, []);

  return (
    <div
      className={
        fullscreen
          ? 'fixed inset-0 z-50 bg-black flex flex-col'
          : 'mt-4 rounded-xl border border-border/50 overflow-hidden'
      }
    >
      {/* 헤더 */}
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b border-border/30">
        <span className="text-sm font-medium text-foreground/80 truncate">{title}</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleDownload} title="HTML 다운로드">
            <Download className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={toggleFullscreen} title={fullscreen ? '축소' : '전체화면'}>
            {fullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </Button>
        </div>
      </div>

      {/* iframe */}
      <iframe
        src={blobUrl}
        className={fullscreen ? 'flex-1 w-full' : 'w-full aspect-video'}
        sandbox="allow-scripts allow-same-origin"
        title="슬라이드 미리보기"
      />
    </div>
  );
}

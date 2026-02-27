'use client';

import { useState, type KeyboardEvent } from 'react';
import { ArrowUp, SlidersHorizontal, X, Link2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { extractVideoId } from '@/lib/constants';

interface UrlInputProps {
  urls: string[];
  onAddUrl: (url: string) => string | null;
  onRemoveUrl: (url: string) => void;
  onToggleSettings: () => void;
  isLoading: boolean;
  onGenerate: () => void;
}

export default function UrlInput({
  urls,
  onAddUrl,
  onRemoveUrl,
  onToggleSettings,
  isLoading,
  onGenerate,
}: UrlInputProps) {
  const [input, setInput] = useState('');
  const [error, setError] = useState('');
  const [focused, setFocused] = useState(false);

  function handleSubmit() {
    const err = onAddUrl(input);
    if (err) {
      setError(err);
      setTimeout(() => setError(''), 3000);
    } else {
      setInput('');
      setError('');
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (input.trim()) {
        handleSubmit();
      } else if (urls.length > 0) {
        onGenerate();
      }
    }
  }

  return (
    <div className="w-full w-full">
      {/* 입력 바 */}
      <div className={`
        relative flex items-center gap-1.5
        border rounded-2xl bg-white px-4 py-2.5
        shadow-sm transition-all duration-200
        ${focused
          ? 'border-primary/40 shadow-[0_0_0_3px_rgba(79,70,229,0.08)] ring-0'
          : 'border-border/60 hover:border-border'}
      `}>
        <Link2 className="h-4 w-4 text-muted-foreground/40 shrink-0" />
        <input
          id="url-input"
          type="url"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="YouTube URL을 붙여넣고 Enter"
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/40"
          aria-label="YouTube 영상 URL 입력"
          disabled={isLoading}
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0 text-muted-foreground/50 hover:text-foreground hover:bg-accent"
          onClick={onToggleSettings}
          aria-label="생성 설정 열기"
        >
          <SlidersHorizontal className="h-4 w-4" />
        </Button>
        <Button
          size="icon"
          className="h-8 w-8 shrink-0 rounded-xl gradient-primary hover:opacity-90 transition-opacity"
          onClick={input.trim() ? handleSubmit : onGenerate}
          disabled={isLoading && !input.trim()}
          aria-label={input.trim() ? 'URL 추가' : '생성 시작'}
        >
          <ArrowUp className="h-4 w-4 text-white" />
        </Button>
      </div>

      {/* 힌트/에러 */}
      {error ? (
        <p className="text-xs text-destructive mt-2 px-2 animate-fade-in">{error}</p>
      ) : (
        <p className="text-[11px] text-muted-foreground/40 mt-2 px-2">
          youtube.com · youtu.be · 최대 10개
        </p>
      )}

      {/* URL 칩 */}
      {urls.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3 animate-fade-in">
          {urls.map((url) => {
            const videoId = extractVideoId(url);
            return (
              <Badge
                key={url}
                variant="secondary"
                className="gap-1.5 pr-1 text-xs font-normal bg-accent/60 border-0 hover:bg-accent transition-colors"
              >
                <span className="max-w-[180px] truncate text-foreground/70">
                  {videoId || url}
                </span>
                <button
                  onClick={() => onRemoveUrl(url)}
                  className="hover:text-destructive rounded-full p-0.5 transition-colors"
                  aria-label={`${videoId} 제거`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            );
          })}
        </div>
      )}
    </div>
  );
}

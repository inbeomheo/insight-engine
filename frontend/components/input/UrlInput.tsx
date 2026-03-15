'use client';

import { useState, useRef, useEffect, memo, type KeyboardEvent, type ClipboardEvent, type DragEvent } from 'react';
import { ArrowUp, SlidersHorizontal, X, Link2, Youtube, Globe, BookOpen, Rss, FileText, Headphones, GripVertical } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import InputWrapper from '@/components/ui/InputWrapper';
import { extractVideoId, detectSourceType, SOURCE_TYPE_LABELS, type SourceType } from '@/lib/constants';

// 소스 타입별 아이콘 + 색상 매핑
const SOURCE_TYPE_ICONS: Record<SourceType, { icon: typeof Globe; colorClass: string }> = {
  youtube: { icon: Youtube,     colorClass: 'text-red-500' },
  arxiv:   { icon: FileText,    colorClass: 'text-purple-500' },
  rss:     { icon: Rss,         colorClass: 'text-orange-500' },
  webpage: { icon: Globe,       colorClass: 'text-blue-500' },
  podcast: { icon: Headphones,  colorClass: 'text-green-500' },
};

// Wikipedia URL 감지
function isWikipediaUrl(url: string): boolean {
  return /wikipedia\.org/i.test(url);
}

interface UrlInputProps {
  urls: string[];
  onAddUrl: (url: string) => string | null;
  onAddUrls: (urls: string[]) => { added: number; errors: string[] };
  onRemoveUrl: (url: string) => void;
  onReorderUrl?: (from: number, to: number) => void;
  onToggleSettings: () => void;
  isLoading: boolean;
  onGenerate: () => void;
}

const UrlInput = memo(function UrlInput({
  urls,
  onAddUrl,
  onAddUrls,
  onRemoveUrl,
  onReorderUrl,
  onToggleSettings,
  isLoading,
  onGenerate,
}: UrlInputProps) {
  const [input, setInput] = useState('');
  const [error, setError] = useState('');
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragIndexRef = useRef<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  // 입력 중 URL 소스 타입 감지 (trim 1회만 수행)
  const trimmedInput = input.trim();
  const inputSourceType = trimmedInput ? detectSourceType(trimmedInput) : null;
  const inputIsWiki = trimmedInput ? isWikipediaUrl(trimmedInput) : false;
  const InputIcon = inputIsWiki
    ? BookOpen
    : inputSourceType
      ? SOURCE_TYPE_ICONS[inputSourceType].icon
      : Link2;
  const inputIconClass = inputIsWiki
    ? 'text-green-600'
    : inputSourceType
      ? SOURCE_TYPE_ICONS[inputSourceType].colorClass
      : 'text-muted-foreground/40';

  // 페이지 로드 시 자동 포커스
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function handleSubmit() {
    const err = onAddUrl(input);
    if (err) {
      setError(err);
      setTimeout(() => setError(''), 3000);
    } else {
      setInput('');
      setError('');
    }
    // URL 추가/에러 후 포커스 유지
    inputRef.current?.focus();
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

  function handlePaste(e: ClipboardEvent) {
    const text = e.clipboardData.getData('text');
    const lines = text.split(/[\n\r]+/).map((l) => l.trim()).filter(Boolean);
    if (lines.length <= 1) return; // 단일 URL은 기본 동작으로 처리

    e.preventDefault();
    const { added, errors } = onAddUrls(lines);
    setInput('');
    if (errors.length > 0) {
      setError(`${added}개 추가됨, ${errors.length}개 유효하지 않은 URL 무시`);
      setTimeout(() => setError(''), 3000);
    }
  }

  return (
    <div className="w-full">
      {/* 입력 바 — InputWrapper로 포커스/에러 스타일 통일 */}
      <InputWrapper focused={focused} error={error} className="flex items-center gap-1.5 px-4 py-2.5">
        <InputIcon className={`h-4 w-4 shrink-0 transition-colors duration-150 ${inputIconClass}`} />
        <input
          ref={inputRef}
          id="url-input"
          type="url"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="URL을 붙여넣고 Enter (YouTube, 웹페이지, RSS, arXiv, Podcast)"
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/40"
          aria-label="URL 입력"
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
          aria-label={input.trim() ? 'URL 추가' : '생성 시작'}
        >
          <ArrowUp className="h-4 w-4 text-white" />
        </Button>
      </InputWrapper>

      {/* 힌트 (에러는 InputWrapper가 표시) */}
      {!error && (
        <p className="text-[11px] text-muted-foreground/40 mt-2 px-2">
          YouTube · 웹페이지 · RSS · arXiv · Podcast · 최대 10개
        </p>
      )}

      {/* URL 칩 (F5-10: 드래그 정렬 지원) */}
      {urls.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3 animate-fade-in">
          {urls.map((url, urlIndex) => {
            const videoId = extractVideoId(url);
            const srcType = detectSourceType(url);
            const isWiki = isWikipediaUrl(url);
            const srcLabel = isWiki ? 'Wikipedia' : SOURCE_TYPE_LABELS[srcType];
            const chipIconEntry = isWiki
              ? { icon: BookOpen, colorClass: 'text-green-600' }
              : SOURCE_TYPE_ICONS[srcType];
            const ChipIcon = chipIconEntry.icon;
            // 칩에 표시할 짧은 레이블: YouTube는 videoId, 나머지는 도메인
            let chipLabel: string;
            if (videoId) {
              chipLabel = videoId;
            } else {
              try {
                chipLabel = new URL(url).hostname.replace(/^www\./, '');
              } catch {
                chipLabel = url.slice(0, 30);
              }
            }
            return (
              <Badge
                key={url}
                variant="secondary"
                className={`gap-1.5 pr-1 text-xs font-normal bg-accent/60 border-0 hover:bg-accent hover:shadow-sm transition-all duration-200 cursor-grab active:cursor-grabbing ${
                  dragOverIndex === urlIndex ? 'ring-2 ring-primary/30' : ''
                }`}
                draggable={urls.length > 1}
                onDragStart={() => { dragIndexRef.current = urlIndex; }}
                onDragOver={(e: DragEvent) => { e.preventDefault(); setDragOverIndex(urlIndex); }}
                onDragLeave={() => setDragOverIndex(null)}
                onDrop={(e: DragEvent) => {
                  e.preventDefault();
                  setDragOverIndex(null);
                  if (dragIndexRef.current !== null && dragIndexRef.current !== urlIndex) {
                    onReorderUrl?.(dragIndexRef.current, urlIndex);
                  }
                  dragIndexRef.current = null;
                }}
                onDragEnd={() => { dragIndexRef.current = null; setDragOverIndex(null); }}
              >
                <GripVertical className="h-3 w-3 shrink-0 text-muted-foreground/30" />
                <ChipIcon className={`h-3 w-3 shrink-0 ${chipIconEntry.colorClass}`} />
                <span className="text-[10px] text-muted-foreground/60 font-medium shrink-0">
                  {srcLabel}
                </span>
                <span className="max-w-[160px] truncate text-foreground/70">
                  {chipLabel}
                </span>
                <button
                  onClick={() => onRemoveUrl(url)}
                  className="hover:text-destructive hover:bg-destructive/10 rounded-full p-0.5 transition-all duration-200 hover:scale-110"
                  aria-label={`${chipLabel} 제거`}
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
});

export default UrlInput;

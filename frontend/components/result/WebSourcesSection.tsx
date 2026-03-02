'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Globe } from 'lucide-react';
import type { WebSource } from '@/lib/types';

interface WebSourcesSectionProps {
  sources: WebSource[];
}

export default function WebSourcesSection({ sources }: WebSourcesSectionProps) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-5 border border-border/50 rounded-lg overflow-hidden">
      {/* 헤더 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-muted/30 hover:bg-muted/50 transition-colors text-sm font-medium"
      >
        <span className="flex items-center gap-2">
          <Globe className="h-3.5 w-3.5 text-muted-foreground" />
          <span>참고 자료 ({sources.length}개 웹 출처)</span>
        </span>
        {open ? (
          <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>

      {/* 출처 목록 */}
      {open && (
        <div className="px-4 py-3 space-y-2.5">
          {sources.map((src, i) => (
            <div key={src.url + i} className="text-sm">
              <a
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-start gap-1.5 text-primary hover:underline font-medium leading-snug"
              >
                <ExternalLink className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                <span>{src.title || src.url}</span>
              </a>
              {src.content && (
                <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed line-clamp-2 pl-5">
                  {src.content}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

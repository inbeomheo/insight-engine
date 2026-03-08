'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Link2 } from 'lucide-react';
import type { InsertedLink } from '@/lib/types';

interface InsertedLinksSectionProps {
  links: InsertedLink[];
}

export default function InsertedLinksSection({ links }: InsertedLinksSectionProps) {
  const [open, setOpen] = useState(false);

  if (!links || links.length === 0) return null;

  const internalLinks = links.filter((l) => l.type === 'internal');
  const externalLinks = links.filter((l) => l.type === 'external');

  return (
    <div className="mt-5 border border-border/50 rounded-lg overflow-hidden">
      {/* 헤더 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="SEO 삽입 링크 섹션 펼치기/접기"
        className="w-full flex items-center justify-between px-4 py-2.5 bg-muted/30 hover:bg-muted/50 transition-colors text-sm font-medium"
      >
        <span className="flex items-center gap-2">
          <Link2 className="h-3.5 w-3.5 text-muted-foreground" />
          <span>SEO 자동 삽입 링크 ({links.length}개)</span>
          <span className="text-xs font-normal text-muted-foreground">
            (내부 {internalLinks.length} · 외부 {externalLinks.length})
          </span>
        </span>
        {open ? (
          <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>

      {/* 링크 목록 */}
      {open && (
        <div className="px-4 py-3 space-y-3">
          {/* 외부링크 */}
          {externalLinks.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">외부 참고 링크</p>
              <div className="space-y-1.5">
                {externalLinks.map((link, i) => (
                  <div key={link.url + i} className="flex items-start gap-2 text-sm">
                    <ExternalLink className="h-3.5 w-3.5 mt-0.5 shrink-0 text-blue-500" />
                    <div className="min-w-0">
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline font-medium leading-snug truncate block"
                      >
                        {link.title || link.url}
                      </a>
                      {link.domain && (
                        <span className="text-xs text-muted-foreground">{link.domain}</span>
                      )}
                      {link.anchor_text && (
                        <span className="text-xs text-muted-foreground ml-2">
                          앵커: &ldquo;{link.anchor_text}&rdquo;
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 내부링크 */}
          {internalLinks.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5">내부 참고 링크 (과거 생성 콘텐츠)</p>
              <div className="space-y-1.5">
                {internalLinks.map((link, i) => (
                  <div key={link.url + i} className="flex items-start gap-2 text-sm">
                    <Link2 className="h-3.5 w-3.5 mt-0.5 shrink-0 text-violet-500" />
                    <div className="min-w-0">
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline font-medium leading-snug truncate block"
                      >
                        {link.title || link.url}
                      </a>
                      {link.anchor_text && (
                        <span className="text-xs text-muted-foreground">
                          앵커: &ldquo;{link.anchor_text}&rdquo;
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

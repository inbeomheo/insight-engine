'use client';

import { useState } from 'react';
import type { FusionMeta, FusionSections as FusionSectionsType } from '@/lib/types';

interface FusionSectionsProps {
  sections?: FusionSectionsType;
  fusionMeta?: FusionMeta;
}

export default function FusionSections({ sections, fusionMeta }: FusionSectionsProps) {
  const [faqOpen, setFaqOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (!sections) return null;

  return (
    <div className="mt-4 space-y-3">
      {fusionMeta && (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-blue-400">
            영상 {fusionMeta.videos_analyzed}개
          </span>
          {fusionMeta.comments_analyzed > 0 && (
            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-green-400">
              댓글 {fusionMeta.comments_analyzed}개
            </span>
          )}
          {fusionMeta.web_sources_found > 0 && (
            <span className="rounded-full bg-purple-500/10 px-2 py-0.5 text-purple-400">
              외부소스 {fusionMeta.web_sources_found}개
            </span>
          )}
        </div>
      )}

      {sections.fact_checks.length > 0 && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-3">
          <p className="mb-2 text-sm font-medium text-yellow-400">팩트체크</p>
          <ul className="space-y-1 text-sm">
            {sections.fact_checks.map((fc, i) => (
              <li key={i} className="text-[var(--text-secondary)]">{fc}</li>
            ))}
          </ul>
        </div>
      )}

      {sections.faq && (
        <div className="rounded-lg border border-[var(--border-primary)]">
          <button
            onClick={() => setFaqOpen(!faqOpen)}
            aria-label="FAQ 섹션 펼치기/접기"
            className="flex w-full items-center justify-between p-3 text-sm font-medium"
          >
            <span>자주 묻는 질문 (FAQ)</span>
            <span>{faqOpen ? '\u25B2' : '\u25BC'}</span>
          </button>
          {faqOpen && (
            <div className="border-t border-[var(--border-primary)] p-3 text-sm whitespace-pre-wrap">
              {sections.faq}
            </div>
          )}
        </div>
      )}

      {sections.sources_used.length > 0 && (
        <div className="rounded-lg border border-[var(--border-primary)]">
          <button
            onClick={() => setSourcesOpen(!sourcesOpen)}
            aria-label="참고 소스 펼치기/접기"
            className="flex w-full items-center justify-between p-3 text-sm font-medium"
          >
            <span>참고 소스 ({sections.sources_used.length}개)</span>
            <span>{sourcesOpen ? '\u25B2' : '\u25BC'}</span>
          </button>
          {sourcesOpen && (
            <div className="border-t border-[var(--border-primary)] p-3">
              <ul className="space-y-1 text-sm">
                {sections.sources_used.map((s, i) => (
                  <li key={i}>
                    <span className="mr-1 text-xs text-[var(--text-tertiary)]">
                      {s.type === 'youtube' ? '\uD83C\uDFAC' : '\uD83D\uDCF0'}
                    </span>
                    <a href={s.url} target="_blank" rel="noopener noreferrer"
                       className="text-[var(--accent-primary)] hover:underline">
                      {s.title}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

'use client';

import { useState } from 'react';

interface LangResult {
  language: string;
  title?: string;
  content?: string;
  html?: string;
  error?: string;
}

interface MultiLangViewProps {
  results: Record<string, LangResult>;
}

const LANG_LABELS: Record<string, string> = {
  ko: '한국어',
  en: 'English',
  ja: '日本語',
};

export default function MultiLangView({ results }: MultiLangViewProps) {
  const languages = Object.keys(results);
  const [activeLang, setActiveLang] = useState(languages[0] || 'ko');

  if (!languages.length) return null;

  const current = results[activeLang];

  return (
    <div className="mt-4 space-y-3">
      {/* 언어 탭 */}
      <div className="flex gap-1 border-b border-border/50 pb-1">
        {languages.map((lang) => (
          <button
            key={lang}
            type="button"
            onClick={() => setActiveLang(lang)}
            className={`px-3 py-1.5 text-sm font-medium rounded-t transition-colors ${
              activeLang === lang
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
            }`}
          >
            {LANG_LABELS[lang] ?? lang}
            {results[lang]?.error && ' (error)'}
          </button>
        ))}
      </div>

      {/* 콘텐츠 */}
      <div className="rounded-lg border border-border/50 bg-muted/10 p-4">
        {current?.error ? (
          <p className="text-sm text-destructive">{current.error}</p>
        ) : current?.html ? (
          <div
            className="prose prose-sm dark:prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: current.html }}
          />
        ) : current?.content ? (
          <pre className="text-sm whitespace-pre-wrap text-foreground/80">
            {current.content}
          </pre>
        ) : (
          <p className="text-sm text-muted-foreground">결과 없음</p>
        )}
      </div>
    </div>
  );
}

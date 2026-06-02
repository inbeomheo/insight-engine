'use client';

import { useEffect, useState } from 'react';
import { ArrowUp, FileText, Link2, Type } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import UrlInput from '@/components/input/UrlInput';
import InputWrapper from '@/components/ui/InputWrapper';
import { cn } from '@/lib/utils';

const MIN_TEXT_CHARS = 50;

export type SourceComposerMode = 'url' | 'text';

interface SourceComposerSnapshot {
  mode: SourceComposerMode;
  text: string;
  textValid: boolean;
}

interface SourceComposerProps {
  urls: string[];
  isLoading: boolean;
  onAddUrl: (url: string) => string | null;
  onAddUrls: (urls: string[]) => { added: number; errors: string[] };
  onRemoveUrl: (url: string) => void;
  onToggleSettings: () => void;
  onGenerateUrl: () => void;
  onGenerateText: (text: string) => void;
  onStateChange?: (snapshot: SourceComposerSnapshot) => void;
}

export default function SourceComposer(props: SourceComposerProps) {
  const { onStateChange } = props;
  const [tab, setTab] = useState<SourceComposerMode>('url');
  const [text, setText] = useState('');
  const [focused, setFocused] = useState(false);
  const trimmedText = text.trim();
  const charCount = trimmedText.length;
  const textValid = charCount >= MIN_TEXT_CHARS;

  useEffect(() => {
    onStateChange?.({ mode: tab, text: trimmedText, textValid });
  }, [onStateChange, tab, trimmedText, textValid]);

  function submitText() {
    if (!textValid || props.isLoading) return;
    props.onGenerateText(trimmedText);
  }

  return (
    <section className="rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Source Composer</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">분석할 소스를 준비하세요</h2>
        </div>
        <div className="flex rounded-full bg-slate-100 p-1 text-xs font-medium">
          <button
            type="button"
            data-testid="source-tab-url"
            onClick={() => setTab('url')}
            className={cn('flex items-center gap-1.5 rounded-full px-3 py-1.5', tab === 'url' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500')}
          >
            <Link2 className="h-3.5 w-3.5" /> URL
          </button>
          <button
            type="button"
            data-testid="source-tab-text"
            onClick={() => setTab('text')}
            className={cn('flex items-center gap-1.5 rounded-full px-3 py-1.5', tab === 'text' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500')}
          >
            <FileText className="h-3.5 w-3.5" /> 텍스트
          </button>
        </div>
      </div>

      {tab === 'url' ? (
        <UrlInput
          urls={props.urls}
          onAddUrl={props.onAddUrl}
          onAddUrls={props.onAddUrls}
          onRemoveUrl={props.onRemoveUrl}
          onToggleSettings={props.onToggleSettings}
          isLoading={props.isLoading}
          onGenerate={props.onGenerateUrl}
        />
      ) : (
        <div>
          <InputWrapper focused={focused} className="px-4 py-3">
            <div className="flex items-start gap-2">
              <Type className="mt-2 h-4 w-4 shrink-0 text-slate-400" />
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder="분석할 텍스트를 직접 입력하세요. 최소 50자 이상이면 하단 Generate Dock에서도 실행할 수 있습니다."
                className="max-h-[220px] min-h-[104px] flex-1 resize-none border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0"
                disabled={props.isLoading}
              />
            </div>
            <div className="mt-2 flex items-center justify-between border-t border-slate-200/70 pt-2">
              <span className={cn('text-[11px]', textValid ? 'text-slate-500' : 'text-amber-600')}>
                {charCount}자{text.length > 0 && !textValid ? ` · 최소 ${MIN_TEXT_CHARS}자 필요` : ''}
              </span>
              <Button
                size="icon"
                className="h-8 w-8 shrink-0 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:opacity-90"
                onClick={submitText}
                disabled={!textValid || props.isLoading}
                aria-label="텍스트로 생성"
              >
                <ArrowUp className="h-4 w-4 text-white" />
              </Button>
            </div>
          </InputWrapper>
          <p className="mt-2 px-2 text-[11px] text-slate-400">
            텍스트 소스도 URL과 동일하게 산출물 설계와 Generate Dock 흐름을 사용합니다.
          </p>
        </div>
      )}
    </section>
  );
}

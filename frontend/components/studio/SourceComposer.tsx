'use client';

import { useState } from 'react';
import { FileText, Link2 } from 'lucide-react';
import UrlInput from '@/components/input/UrlInput';
import TextInput from '@/components/input/TextInput';
import { cn } from '@/lib/utils';

interface SourceComposerProps {
  urls: string[];
  isLoading: boolean;
  onAddUrl: (url: string) => string | null;
  onAddUrls: (urls: string[]) => { added: number; errors: string[] };
  onRemoveUrl: (url: string) => void;
  onToggleSettings: () => void;
  onGenerateUrl: () => void;
  onGenerateText: (text: string) => void;
}

export default function SourceComposer(props: SourceComposerProps) {
  const [tab, setTab] = useState<'url' | 'text'>('url');

  return (
    <section className="rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Source Composer</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">분석할 소스를 준비하세요</h2>
        </div>
        <div className="flex rounded-full bg-slate-100 p-1 text-xs font-medium">
          <button type="button" onClick={() => setTab('url')} className={cn('flex items-center gap-1.5 rounded-full px-3 py-1.5', tab === 'url' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500')}><Link2 className="h-3.5 w-3.5" /> URL</button>
          <button type="button" onClick={() => setTab('text')} className={cn('flex items-center gap-1.5 rounded-full px-3 py-1.5', tab === 'text' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500')}><FileText className="h-3.5 w-3.5" /> 텍스트</button>
        </div>
      </div>
      {tab === 'url' ? (
        <UrlInput urls={props.urls} onAddUrl={props.onAddUrl} onAddUrls={props.onAddUrls} onRemoveUrl={props.onRemoveUrl} onToggleSettings={props.onToggleSettings} isLoading={props.isLoading} onGenerate={props.onGenerateUrl} />
      ) : (
        <TextInput onGenerate={props.onGenerateText} isLoading={props.isLoading} />
      )}
    </section>
  );
}

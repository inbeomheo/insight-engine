'use client';

import { useEffect, useState, type ChangeEvent } from 'react';
import { ArrowUp, FileAudio, FileText, Link2, Mic, Type, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import UrlInput from '@/components/input/UrlInput';
import FileUpload from '@/components/input/FileUpload';
import VoiceRecorder from '@/components/input/VoiceRecorder';
import InputWrapper from '@/components/ui/InputWrapper';
import { cn } from '@/lib/utils';

const MIN_TEXT_CHARS = 50;

export type SourceComposerMode = 'url' | 'text' | 'file' | 'voice';

export interface SourceComposerSnapshot {
  mode: SourceComposerMode;
  text: string;
  textValid: boolean;
  file: File | null;
  audioFile: File | null;
}

interface SourceComposerProps {
  urls: string[];
  isLoading: boolean;
  onAddUrl: (url: string) => string | null;
  onAddUrls: (urls: string[]) => { added: number; errors: string[] };
  onRemoveUrl: (url: string) => void;
  onReorderUrl?: (from: number, to: number) => void;
  onToggleSettings: () => void;
  onGenerateUrl: () => void;
  onGenerateText: (text: string) => void | Promise<boolean>;
  onGenerateFile: (file: File) => void | Promise<boolean>;
  onGenerateAudio: (file: File) => void | Promise<boolean>;
  onStateChange?: (snapshot: SourceComposerSnapshot) => void;
}

const tabs: Array<{ id: SourceComposerMode; label: string; icon: typeof Link2; testId: string }> = [
  { id: 'url', label: 'URL', icon: Link2, testId: 'source-tab-url' },
  { id: 'text', label: '텍스트', icon: FileText, testId: 'source-tab-text' },
  { id: 'file', label: '파일', icon: Upload, testId: 'source-tab-file' },
  { id: 'voice', label: '음성', icon: Mic, testId: 'source-tab-voice' },
];

export default function SourceComposer(props: SourceComposerProps) {
  const { onStateChange } = props;
  const [tab, setTab] = useState<SourceComposerMode>('url');
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [focused, setFocused] = useState(false);
  const trimmedText = text.trim();
  const charCount = trimmedText.length;
  const textValid = charCount >= MIN_TEXT_CHARS;

  useEffect(() => {
    onStateChange?.({ mode: tab, text: trimmedText, textValid, file, audioFile });
  }, [onStateChange, tab, trimmedText, textValid, file, audioFile]);

  function submitText() {
    if (!textValid || props.isLoading) return;
    props.onGenerateText(trimmedText);
  }

  function submitFile() {
    if (!file || props.isLoading) return;
    props.onGenerateFile(file);
  }

  function submitAudio() {
    if (!audioFile || props.isLoading) return;
    props.onGenerateAudio(audioFile);
  }

  function handleAudioUpload(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    if (nextFile) setAudioFile(nextFile);
    event.target.value = '';
  }

  return (
    <section className="rounded-[24px] border border-slate-200/80 bg-white p-4 shadow-sm shadow-slate-200/60 sm:p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Source Composer</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-950">분석할 소스를 준비하세요</h2>
        </div>
        <div className="grid grid-cols-4 rounded-full bg-slate-100 p-1 text-xs font-medium">
          {tabs.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                type="button"
                data-testid={item.testId}
                onClick={() => setTab(item.id)}
                className={cn(
                  'flex items-center justify-center gap-1.5 rounded-full px-3 py-1.5',
                  tab === item.id ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500',
                )}
              >
                <Icon className="h-3.5 w-3.5" /> {item.label}
              </button>
            );
          })}
        </div>
      </div>

      {tab === 'url' && (
        <UrlInput
          urls={props.urls}
          onAddUrl={props.onAddUrl}
          onAddUrls={props.onAddUrls}
          onRemoveUrl={props.onRemoveUrl}
          onReorderUrl={props.onReorderUrl}
          onToggleSettings={props.onToggleSettings}
          isLoading={props.isLoading}
          onGenerate={props.onGenerateUrl}
        />
      )}

      {tab === 'text' && (
        <div data-testid="text-source-panel">
          <InputWrapper focused={focused} className="px-4 py-3">
            <div className="flex items-start gap-2">
              <Type className="mt-2 h-4 w-4 shrink-0 text-slate-400" />
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder="영상 설명이나 원고를 붙여넣으세요. 최소 50자 이상이면 아래 Generate Dock에서 생성할 수 있습니다."
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
                aria-label="텍스트 생성"
              >
                <ArrowUp className="h-4 w-4 text-white" />
              </Button>
            </div>
          </InputWrapper>
          <p className="mt-2 px-2 text-[11px] text-slate-400">
            텍스트 소스는 URL 없이도 바로 Generate Dock으로 생성됩니다.
          </p>
        </div>
      )}

      {tab === 'file' && (
        <div data-testid="file-source-panel" className="space-y-3">
          <FileUpload file={file} onFileSelect={setFile} disabled={props.isLoading} />
          <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-3 py-2 text-xs text-slate-500">
            <span>PDF/DOCX를 업로드하면 문서 내용을 분석해 콘텐츠를 만듭니다.</span>
            <Button size="sm" className="h-8 rounded-xl" onClick={submitFile} disabled={!file || props.isLoading}>
              파일 생성
            </Button>
          </div>
        </div>
      )}

      {tab === 'voice' && (
        <div data-testid="voice-source-panel" className="space-y-3 rounded-2xl border border-slate-200/80 bg-slate-50/60 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">녹음하거나 오디오 파일 업로드</p>
              <p className="mt-1 text-xs text-slate-500">회의·강의·팟캐스트 MP3/WAV/WEBM 파일을 분석합니다.</p>
            </div>
            <VoiceRecorder onRecordingComplete={setAudioFile} disabled={props.isLoading} />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-medium text-slate-600 shadow-sm hover:border-indigo-200 hover:text-indigo-700">
              <FileAudio className="h-3.5 w-3.5" />
              오디오 파일 선택
              <input
                data-testid="voice-file-input"
                type="file"
                accept="audio/*,.mp3,.wav,.webm,.m4a"
                className="sr-only"
                onChange={handleAudioUpload}
                disabled={props.isLoading}
              />
            </label>
            {audioFile && (
              <div className="inline-flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-xs text-slate-600 shadow-sm">
                <FileAudio className="h-3.5 w-3.5 text-indigo-600" />
                <span className="max-w-[220px] truncate">{audioFile.name}</span>
                <button type="button" className="text-slate-400 hover:text-red-500" onClick={() => setAudioFile(null)}>
                  제거
                </button>
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <Button size="sm" className="h-8 rounded-xl" onClick={submitAudio} disabled={!audioFile || props.isLoading}>
              음성 생성
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

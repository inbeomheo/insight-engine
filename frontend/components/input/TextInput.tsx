'use client';

import { useState, useCallback, useRef } from 'react';
import type { ChangeEvent } from 'react';
import { ArrowUp, FileText, Loader2, Type } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import InputWrapper from '@/components/ui/InputWrapper';
import { extractAudio, extractDocument } from '@/lib/api';

// 최소/최대 길이는 서버 config.DIRECT_TEXT_MIN_CHARS / DIRECT_TEXT_MAX_CHARS와 맞춘다.
const MIN_CHARS = 50;
const MAX_CHARS = 200000;
const AUDIO_EXTENSIONS = new Set(['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac']);

function getFileExtension(file: File): string {
  const dotIndex = file.name.lastIndexOf('.');
  return dotIndex >= 0 ? file.name.slice(dotIndex).toLowerCase() : '';
}

interface TextInputProps {
  value: string;
  onChange: (text: string) => void;
  onGenerate: (text: string) => void;
  isLoading: boolean;
}

export default function TextInput({ value, onChange, onGenerate, isLoading }: TextInputProps) {
  const [focused, setFocused] = useState(false);
  const [isExtractingFile, setIsExtractingFile] = useState(false);
  const [fileNotice, setFileNotice] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const charCount = value.length;
  const isValid = charCount >= MIN_CHARS && charCount <= MAX_CHARS;
  const overLimit = charCount > MAX_CHARS;

  const handleSubmit = useCallback(() => {
    if (!isValid || isLoading) return;
    onGenerate(value.trim());
  }, [value, isValid, isLoading, onGenerate]);

  const handleTextChange = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    setFileError(null);
    setFileNotice(null);
    onChange(e.target.value);
  }, [onChange]);

  const handleFileClick = useCallback(() => {
    if (isLoading || isExtractingFile) return;
    fileInputRef.current?.click();
  }, [isLoading, isExtractingFile]);

  const handleFileChange = useCallback(async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    if (value.trim() && !window.confirm('기존 입력 내용을 파일 추출 텍스트로 교체할까요?')) {
      return;
    }

    setIsExtractingFile(true);
    setFileError(null);
    setFileNotice(null);
    try {
      const isAudio = AUDIO_EXTENSIONS.has(getFileExtension(file));
      const result = isAudio ? await extractAudio(file) : await extractDocument(file);
      onChange(result.text.slice(0, MAX_CHARS));
      if (result.truncated) {
        setFileNotice(`${isAudio ? '음성 전사' : '문서'} 내용이 최대 길이에 맞춰 일부 잘렸습니다.`);
      }
    } catch (err) {
      setFileError(err instanceof Error ? err.message : '파일을 불러오지 못했습니다.');
    } finally {
      setIsExtractingFile(false);
    }
  }, [onChange, value]);

  return (
    <div>
      <InputWrapper focused={focused} className="border-[1.5px] border-foreground px-4 py-3 signal-input-shadow">
        <div className="flex items-start gap-2">
          <Type className="h-4 w-4 text-muted-foreground/40 shrink-0 mt-2" />
          <Textarea
            value={value}
            onChange={handleTextChange}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="분석할 텍스트를 직접 입력하세요 (최소 50자)"
            maxLength={MAX_CHARS}
            className="flex-1 min-h-[80px] max-h-[200px] bg-transparent text-sm border-0 shadow-none resize-none p-0 focus-visible:ring-0 placeholder:text-muted-foreground/40"
            disabled={isLoading}
          />
        </div>

        {/* 하단: 글자수 + 생성 버튼 */}
        <div className="flex items-center justify-between gap-3 mt-2 pt-2 border-t border-border/30">
          <div className="min-w-0">
            <span className={`signal-meta text-[10px] ${overLimit ? 'text-destructive' : isValid ? 'text-muted-foreground/60' : 'text-amber-500'}`}>
              {charCount.toLocaleString()}자 / {MAX_CHARS.toLocaleString()}자
              {!isValid && charCount > 0 && charCount < MIN_CHARS && ` (최소 ${MIN_CHARS}자)`}
            </span>
            {fileNotice && (
              <p className="mt-1 text-[11px] text-amber-600">{fileNotice}</p>
            )}
            {fileError && (
              <p className="mt-1 text-[11px] text-destructive" role="alert">{fileError}</p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.pptx,.mp3,.wav,.m4a,.ogg,.flac,.aac"
              className="hidden"
              onChange={handleFileChange}
              disabled={isLoading || isExtractingFile}
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 gap-1.5 rounded-sm text-xs"
              onClick={handleFileClick}
              disabled={isLoading || isExtractingFile}
              aria-label="파일 불러오기"
            >
              {isExtractingFile ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <FileText className="h-3.5 w-3.5" />
              )}
              파일 불러오기
            </Button>
            <Button
              size="icon"
              className="h-9 w-9 shrink-0 rounded-sm"
              onClick={handleSubmit}
              disabled={!isValid || isLoading}
              aria-label="텍스트로 생성"
            >
              <ArrowUp className="h-4 w-4 text-white" />
            </Button>
          </div>
        </div>
      </InputWrapper>

      <p className="signal-meta text-[10px] text-muted-foreground/55 mt-3 px-1">
        텍스트를 직접 입력하면 URL 없이 콘텐츠를 생성합니다
      </p>
    </div>
  );
}

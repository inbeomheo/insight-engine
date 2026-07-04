'use client';

import { useState, useCallback } from 'react';
import { ArrowUp, Type } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import InputWrapper from '@/components/ui/InputWrapper';

// 최소/최대 길이는 서버 config.DIRECT_TEXT_MIN_CHARS / DIRECT_TEXT_MAX_CHARS와 맞춘다.
const MIN_CHARS = 50;
const MAX_CHARS = 200000;

interface TextInputProps {
  value: string;
  onChange: (text: string) => void;
  onGenerate: (text: string) => void;
  isLoading: boolean;
}

export default function TextInput({ value, onChange, onGenerate, isLoading }: TextInputProps) {
  const [focused, setFocused] = useState(false);

  const charCount = value.length;
  const isValid = charCount >= MIN_CHARS && charCount <= MAX_CHARS;
  const overLimit = charCount > MAX_CHARS;

  const handleSubmit = useCallback(() => {
    if (!isValid || isLoading) return;
    onGenerate(value.trim());
  }, [value, isValid, isLoading, onGenerate]);

  return (
    <div>
      <InputWrapper focused={focused} className="border-[1.5px] border-foreground px-4 py-3 signal-input-shadow">
        <div className="flex items-start gap-2">
          <Type className="h-4 w-4 text-muted-foreground/40 shrink-0 mt-2" />
          <Textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="분석할 텍스트를 직접 입력하세요 (최소 50자)"
            maxLength={MAX_CHARS}
            className="flex-1 min-h-[80px] max-h-[200px] bg-transparent text-sm border-0 shadow-none resize-none p-0 focus-visible:ring-0 placeholder:text-muted-foreground/40"
            disabled={isLoading}
          />
        </div>

        {/* 하단: 글자수 + 생성 버튼 */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/30">
          <span className={`signal-meta text-[10px] ${overLimit ? 'text-destructive' : isValid ? 'text-muted-foreground/60' : 'text-amber-500'}`}>
            {charCount.toLocaleString()}자 / {MAX_CHARS.toLocaleString()}자
            {!isValid && charCount > 0 && charCount < MIN_CHARS && ` (최소 ${MIN_CHARS}자)`}
          </span>
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
      </InputWrapper>

      <p className="signal-meta text-[10px] text-muted-foreground/55 mt-3 px-1">
        텍스트를 직접 입력하면 URL 없이 콘텐츠를 생성합니다
      </p>
    </div>
  );
}

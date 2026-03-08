'use client';

import { useState, useCallback } from 'react';
import { ArrowUp, Type } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import InputWrapper from '@/components/ui/InputWrapper';

const MIN_CHARS = 50;

interface TextInputProps {
  onGenerate: (text: string) => void;
  isLoading: boolean;
}

export default function TextInput({ onGenerate, isLoading }: TextInputProps) {
  const [text, setText] = useState('');
  const [focused, setFocused] = useState(false);

  const charCount = text.length;
  const isValid = charCount >= MIN_CHARS;

  const handleSubmit = useCallback(() => {
    if (!isValid || isLoading) return;
    onGenerate(text.trim());
  }, [text, isValid, isLoading, onGenerate]);

  return (
    <div>
      <InputWrapper focused={focused} className="px-4 py-3">
        <div className="flex items-start gap-2">
          <Type className="h-4 w-4 text-muted-foreground/40 shrink-0 mt-2" />
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="분석할 텍스트를 직접 입력하세요 (최소 50자)"
            className="flex-1 min-h-[80px] max-h-[200px] bg-transparent text-sm border-0 shadow-none resize-none p-0 focus-visible:ring-0 placeholder:text-muted-foreground/40"
            disabled={isLoading}
          />
        </div>

        {/* 하단: 글자수 + 생성 버튼 */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-border/30">
          <span className={`text-[11px] ${isValid ? 'text-muted-foreground/50' : 'text-amber-500'}`}>
            {charCount}자 {!isValid && charCount > 0 && `(최소 ${MIN_CHARS}자)`}
          </span>
          <Button
            size="icon"
            className="h-8 w-8 shrink-0 rounded-xl gradient-primary hover:opacity-90 transition-opacity"
            onClick={handleSubmit}
            disabled={!isValid || isLoading}
            aria-label="텍스트로 생성"
          >
            <ArrowUp className="h-4 w-4 text-white" />
          </Button>
        </div>
      </InputWrapper>

      <p className="text-[11px] text-muted-foreground/40 mt-2 px-2">
        텍스트를 직접 입력하면 URL 없이 콘텐츠를 생성합니다
      </p>
    </div>
  );
}

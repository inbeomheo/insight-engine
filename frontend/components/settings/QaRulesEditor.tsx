'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Plus, ShieldCheck } from 'lucide-react';
import { useListManager } from '@/hooks/useListManager';

// 기본 금칙어 (config.py의 QA_FORBIDDEN_WORDS와 동기화)
const DEFAULT_FORBIDDEN_WORDS = [
  '놀라운', '혁신적', '획기적', '최고의', '게임체인저',
  '압도적', '경이로운', '드디어', '탁월한', '인상적', '뛰어난', '강력한',
];

interface QaRulesEditorProps {
  forbiddenWords: string[];
  onChange: (words: string[]) => void;
}

export default function QaRulesEditor({ forbiddenWords, onChange }: QaRulesEditorProps) {
  const [input, setInput] = useState('');
  const words = useListManager<string>(forbiddenWords);

  // props 변경 시 내부 리스트 동기화
  useEffect(() => {
    words.set(forbiddenWords);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [forbiddenWords]);

  function handleAdd() {
    const word = input.trim();
    if (!word || words.items.includes(word)) {
      setInput('');
      return;
    }
    onChange([...words.items, word]);
    setInput('');
  }

  function handleRemove(word: string) {
    onChange(words.items.filter((w) => w !== word));
  }

  function handleReset() {
    onChange([...DEFAULT_FORBIDDEN_WORDS]);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          QA 금칙어 규칙
        </h4>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs h-7"
          onClick={handleReset}
        >
          기본값 복원
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">
        생성된 콘텐츠에서 감지할 금칙어를 관리합니다.
      </p>

      {/* 입력 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="금칙어 추가..."
          className="flex-1 text-xs rounded-md border px-3 py-2 bg-background focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <Button
          variant="outline"
          size="sm"
          className="h-auto px-3"
          onClick={handleAdd}
          disabled={!input.trim()}
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* 태그 목록 */}
      <div className="flex flex-wrap gap-1.5">
        {words.items.map((word) => (
          <Badge
            key={word}
            variant="secondary"
            className="text-xs gap-1 pr-1"
          >
            {word}
            <button
              type="button"
              onClick={() => handleRemove(word)}
              aria-label={`${word} 금칙어 제거`}
              className="ml-0.5 rounded-full hover:bg-destructive/20 p-0.5 transition-colors"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        {words.items.length === 0 && (
          <p className="text-xs text-muted-foreground">금칙어가 없습니다.</p>
        )}
      </div>
    </div>
  );
}

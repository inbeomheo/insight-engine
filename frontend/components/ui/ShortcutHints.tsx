'use client';

import { useState } from 'react';
import { Keyboard, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

/** 단축키 목록 */
const SHORTCUTS = [
  { category: '일반', items: [
    { keys: ['Ctrl', 'K'], label: '커맨드 팔레트' },
    { keys: ['Ctrl', ','], label: '설정 열기' },
    { keys: ['Ctrl', 'B'], label: '사이드바 토글' },
  ]},
  { category: '탐색', items: [
    { keys: ['Alt', '1'], label: '메인 뷰' },
    { keys: ['Alt', '2'], label: '캘린더 뷰' },
  ]},
  { category: '편집', items: [
    { keys: ['Esc'], label: '모달 닫기' },
    { keys: ['Enter'], label: 'URL 추가 / 생성 시작' },
  ]},
];

/** 단축키 힌트 오버레이 (F5-07) */
export default function ShortcutHints() {
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground/40 hover:text-foreground"
        onClick={() => setOpen(true)}
        aria-label="키보드 단축키"
      >
        <Keyboard className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-md mx-4 bg-white rounded-xl shadow-2xl border border-border/60 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold">키보드 단축키</h2>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setOpen(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="space-y-5">
          {SHORTCUTS.map((group) => (
            <div key={group.category}>
              <h3 className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider mb-2">
                {group.category}
              </h3>
              <div className="space-y-1.5">
                {group.items.map((item) => (
                  <div key={item.label} className="flex items-center justify-between text-sm">
                    <span className="text-foreground/80">{item.label}</span>
                    <div className="flex items-center gap-1">
                      {item.keys.map((k) => (
                        <kbd
                          key={k}
                          className="min-w-[24px] px-1.5 py-0.5 text-[11px] text-center font-mono
                                     bg-muted/60 border border-border/40 rounded text-muted-foreground"
                        >
                          {k}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

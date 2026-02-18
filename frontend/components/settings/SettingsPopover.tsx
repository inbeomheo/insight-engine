'use client';

import { useRef, useEffect } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';
import { useUIStore } from '@/stores/uiStore';
import { STYLE_OPTIONS, LENGTH_OPTIONS, WRITING_STYLE_OPTIONS } from '@/lib/constants';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';

export default function SettingsPopover() {
  const { settingsPopoverOpen, setSettingsPopoverOpen } = useUIStore();
  const {
    providers,
    selectedProvider,
    selectedModel,
    selectedStyle,
    modifiers,
    customStyles,
    setSelectedProvider,
    setSelectedModel,
    setSelectedStyle,
    setModifiers,
  } = useSettingsStore();

  const ref = useRef<HTMLDivElement>(null);

  // 외부 클릭 감지
  useEffect(() => {
    if (!settingsPopoverOpen) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setSettingsPopoverOpen(false);
      }
    }
    // 약간의 딜레이로 열기 클릭 이벤트와 겹치지 않게
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClick);
    }, 10);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClick);
    };
  }, [settingsPopoverOpen, setSettingsPopoverOpen]);

  if (!settingsPopoverOpen) return null;

  const providerIds = Object.keys(providers);
  const currentModels = selectedProvider ? providers[selectedProvider]?.models || [] : [];

  // 내장 + 커스텀 스타일
  const allStyles = [
    ...STYLE_OPTIONS,
    ...customStyles.map((c) => ({ id: c.id, label: c.name, emoji: c.icon || '✨' })),
  ];

  return (
    <div
      ref={ref}
      className="absolute left-1/2 -translate-x-1/2 top-full mt-2 z-40 w-[420px] bg-popover border border-border rounded-xl shadow-lg p-5 space-y-5"
    >
      {/* AI 모델 */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-2 block">AI 모델</label>
        <div className="flex gap-2">
          <Select
            value={selectedProvider}
            onValueChange={(v) => {
              setSelectedProvider(v);
              const first = providers[v]?.models[0];
              if (first) setSelectedModel(first.id);
            }}
          >
            <SelectTrigger className="h-9 text-sm flex-1">
              <SelectValue placeholder="서비스" />
            </SelectTrigger>
            <SelectContent>
              {providerIds.map((id) => (
                <SelectItem key={id} value={id} className="text-sm">
                  {providers[id].name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="h-9 text-sm flex-1">
              <SelectValue placeholder="모델" />
            </SelectTrigger>
            <SelectContent>
              {currentModels.map((m) => (
                <SelectItem key={m.id} value={m.id} className="text-sm">
                  {m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 스타일 */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-2 block">스타일</label>
        <div className="flex flex-wrap gap-2">
          {allStyles.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedStyle(s.id)}
              className={cn(
                'px-3 py-1.5 rounded-full text-sm border transition-all',
                selectedStyle === s.id
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-foreground border-border hover:border-primary/50'
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* 길이 */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-2 block">길이</label>
        <div className="flex gap-2">
          {LENGTH_OPTIONS.map((o) => (
            <button
              key={o.value}
              onClick={() => setModifiers({ length: o.value })}
              className={cn(
                'flex-1 px-3 py-2 rounded-lg text-sm border transition-all text-center',
                modifiers.length === o.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-foreground border-border hover:border-primary/50'
              )}
            >
              <div className="font-medium">{o.label}</div>
              <div className="text-xs opacity-70 mt-0.5">{o.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* 문체 */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-2 block">문체</label>
        <div className="flex gap-2">
          {WRITING_STYLE_OPTIONS.map((o) => (
            <button
              key={o.value}
              onClick={() => setModifiers({ writing_style: o.value })}
              className={cn(
                'flex-1 px-3 py-2 rounded-lg text-sm border transition-all',
                modifiers.writing_style === o.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-foreground border-border hover:border-primary/50'
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

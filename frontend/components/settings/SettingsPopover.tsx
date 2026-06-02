'use client';

import { useRef, useEffect, useState } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';
import { useUIStore } from '@/stores/uiStore';
import { STYLE_OPTIONS, LENGTH_OPTIONS, WRITING_STYLE_OPTIONS, LANGUAGE_OPTIONS } from '@/lib/constants';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { testWebhook } from '@/lib/api';
import KnowledgeManager from './KnowledgeManager';

export default function SettingsPopover() {
  const { settingsPopoverOpen, setSettingsPopoverOpen } = useUIStore();
  const {
    providers,
    selectedProvider,
    selectedModel,
    selectedStyle,
    modifiers,
    customStyles,
    ollamaBaseUrl,
    webhookUrl,
    wordpressDefaults,
    naverDefaults,
    enableWebSearch,
    setSelectedProvider,
    setSelectedModel,
    setSelectedStyle,
    setModifiers,
    setOllamaBaseUrl,
    setWebhookUrl,
    setWordPressDefaults,
    setNaverDefaults,
    setEnableWebSearch,
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

  // ESC 키로 닫기
  useEffect(() => {
    if (!settingsPopoverOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setSettingsPopoverOpen(false);
      }
    }
    // capture 단계에서 먼저 잡기 (다른 컴포넌트가 가로채지 못하게)
    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
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
      role="dialog"
      aria-label="생성 설정"
      aria-describedby="settings-popover-desc"
      className="fixed left-1/2 top-20 z-40 max-h-[calc(100vh-6rem)] w-[420px] max-w-[calc(100vw-2rem)] -translate-x-1/2 overflow-y-auto overscroll-contain rounded-xl border border-border bg-popover p-5 shadow-lg space-y-5"
    >
      <p id="settings-popover-desc" className="sr-only">AI 모델, 스타일, 길이, 문체, 언어 등 콘텐츠 생성 옵션을 설정합니다.</p>
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
              aria-label={`${s.label} 스타일 선택`}
              aria-pressed={selectedStyle === s.id}
              className={cn(
                'px-3 py-1.5 rounded-full text-sm border transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-1 active:scale-95',
                selectedStyle === s.id
                  ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                  : 'bg-background text-foreground border-border hover:border-primary/50 hover:shadow-sm'
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
              aria-label={`${o.label} 길이 선택`}
              aria-pressed={modifiers.length === o.value}
              className={cn(
                'flex-1 px-3 py-2 rounded-lg text-sm border transition-all duration-200 text-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-1 active:scale-95',
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
              aria-label={`${o.label} 문체 선택`}
              aria-pressed={modifiers.writing_style === o.value}
              className={cn(
                'flex-1 px-3 py-2 rounded-lg text-sm border transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-1 active:scale-95',
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

      {/* 출력 언어 */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-2 block">출력 언어</label>
        <div className="flex gap-2">
          {LANGUAGE_OPTIONS.map((o) => (
            <button
              key={o.value}
              onClick={() => setModifiers({ language: o.value })}
              aria-label={`${o.label} 언어 선택`}
              aria-pressed={(modifiers.language ?? 'ko') === o.value}
              className={cn(
                'flex-1 px-3 py-2 rounded-lg text-sm border transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-1 active:scale-95',
                (modifiers.language ?? 'ko') === o.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-foreground border-border hover:border-primary/50'
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Ollama 설정 — ollama 프로바이더 선택 시만 표시 */}
      {selectedProvider === 'ollama' && (
        <div>
          <label className="text-sm font-medium text-muted-foreground mb-2 block">
            Ollama Base URL
          </label>
          <input
            type="text"
            value={ollamaBaseUrl}
            onChange={(e) => setOllamaBaseUrl(e.target.value)}
            placeholder="http://localhost:11434"
            className="w-full h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Ollama 서버 주소 (기본: http://localhost:11434)
          </p>
        </div>
      )}

      {/* 웹 검색 보강 */}
      <div>
        <label className="text-sm font-medium text-muted-foreground mb-2 block">생성 옵션</label>
        <button
          onClick={() => setEnableWebSearch(!enableWebSearch)}
          role="switch"
          aria-checked={enableWebSearch}
          aria-label="웹 검색 보강 토글"
          className={cn(
            'w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm border transition-all',
            enableWebSearch
              ? 'bg-primary/10 text-primary border-primary/40'
              : 'bg-background text-foreground border-border hover:border-primary/50'
          )}
        >
          <span>웹 검색 보강 (Grounded Generation)</span>
          <span className={cn(
            'w-9 h-5 rounded-full transition-colors relative shrink-0',
            enableWebSearch ? 'bg-primary' : 'bg-muted'
          )}>
            <span className={cn(
              'absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform',
              enableWebSearch ? 'translate-x-4' : 'translate-x-0'
            )} />
          </span>
        </button>
        {enableWebSearch && (
          <p className="text-xs text-muted-foreground mt-1.5">
            Tavily API로 웹 검색 결과를 AI 프롬프트에 주입합니다. TAVILY_API_KEY 설정 필요.
          </p>
        )}
      </div>

      {/* 웹훅 연동 */}
      <WebhookSection webhookUrl={webhookUrl} setWebhookUrl={setWebhookUrl} />
      <WordPressDefaultsSection
        defaults={wordpressDefaults}
        setDefaults={setWordPressDefaults}
      />
      <NaverDefaultsSection
        defaults={naverDefaults}
        setDefaults={setNaverDefaults}
      />

      {/* 지식 베이스 */}
      <KnowledgeManager />
    </div>
  );
}

function NaverDefaultsSection({
  defaults,
  setDefaults,
}: {
  defaults: { webhook_url: string; blog_id: string; category: string; tags: string };
  setDefaults: (defaults: Partial<{ webhook_url: string; blog_id: string; category: string; tags: string }>) => void;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-muted-foreground mb-2 block">
        네이버 블로그 예약 기본값
      </label>
      <div className="grid gap-2">
        <input
          data-testid="settings-naver-webhook-url"
          type="url"
          value={defaults.webhook_url}
          onChange={(e) => setDefaults({ webhook_url: e.target.value })}
          placeholder="네이버 발행 웹훅 URL"
          className="h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          data-testid="settings-naver-blog-id"
          value={defaults.blog_id}
          onChange={(e) => setDefaults({ blog_id: e.target.value })}
          placeholder="블로그 ID"
          className="h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          data-testid="settings-naver-category"
          value={defaults.category}
          onChange={(e) => setDefaults({ category: e.target.value })}
          placeholder="카테고리"
          className="h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          data-testid="settings-naver-tags"
          value={defaults.tags}
          onChange={(e) => setDefaults({ tags: e.target.value })}
          placeholder="태그, 쉼표로 구분"
          className="h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>
      <p className="text-xs text-muted-foreground mt-1">
        예약 발행에서 반복 입력하는 네이버 옵션을 미리 채웁니다.
      </p>
    </div>
  );
}

function WordPressDefaultsSection({
  defaults,
  setDefaults,
}: {
  defaults: { site_url: string; username: string; status: string };
  setDefaults: (defaults: Partial<{ site_url: string; username: string; status: string }>) => void;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-muted-foreground mb-2 block">
        WordPress 예약 기본값
      </label>
      <div className="grid gap-2">
        <input
          data-testid="settings-wordpress-site-url"
          type="url"
          value={defaults.site_url}
          onChange={(e) => setDefaults({ site_url: e.target.value })}
          placeholder="https://example.com"
          className="h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <input
          data-testid="settings-wordpress-username"
          value={defaults.username}
          onChange={(e) => setDefaults({ username: e.target.value })}
          placeholder="WordPress 사용자명"
          className="h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <select
          data-testid="settings-wordpress-status"
          value={defaults.status}
          onChange={(e) => setDefaults({ status: e.target.value })}
          className="h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        >
          <option value="draft">임시글</option>
          <option value="publish">즉시 공개</option>
          <option value="pending">검토 대기</option>
          <option value="private">비공개</option>
        </select>
      </div>
      <p className="text-xs text-muted-foreground mt-1">
        Application Password는 보안을 위해 예약 등록 시에만 입력합니다.
      </p>
    </div>
  );
}

function WebhookSection({
  webhookUrl,
  setWebhookUrl,
}: {
  webhookUrl: string;
  setWebhookUrl: (url: string) => void;
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string } | null>(null);

  async function handleTest() {
    if (!webhookUrl.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testWebhook(webhookUrl.trim());
      setTestResult(res);
    } catch (err) {
      setTestResult({ success: false, error: err instanceof Error ? err.message : '전송 실패' });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div>
      <label className="text-sm font-medium text-muted-foreground mb-2 block">
        웹훅 연동
      </label>
      <div className="flex gap-2">
        <input
          type="url"
          value={webhookUrl}
          onChange={(e) => {
            setWebhookUrl(e.target.value);
            setTestResult(null);
          }}
          placeholder="https://n8n.example.com/webhook/..."
          className="flex-1 h-9 px-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <button
          onClick={handleTest}
          disabled={testing || !webhookUrl.trim()}
          aria-label="웹훅 테스트"
          className={cn(
            'h-9 px-3 text-sm rounded-lg border transition-all whitespace-nowrap',
            'bg-background text-foreground border-border hover:border-primary/50',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          {testing ? '...' : '테스트'}
        </button>
      </div>
      {testResult && (
        <p className={cn('text-xs mt-1', testResult.success ? 'text-green-500' : 'text-red-500')}>
          {testResult.success ? '전송 성공' : `실패: ${testResult.error}`}
        </p>
      )}
      <p className="text-xs text-muted-foreground mt-1">
        n8n, Make, Zapier 웹훅 URL (콘텐츠 생성 시 자동 전송)
      </p>
    </div>
  );
}

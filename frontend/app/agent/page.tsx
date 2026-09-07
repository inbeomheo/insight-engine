'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Bot, Send, Square, Plus, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import ChatMessage from './components/ChatMessage';
import { useAgentChat } from './hooks/useAgentChat';
import { cn } from '@/lib/utils';
import { useAuthUserId } from '@/hooks/useAuthUserId';

export default function AgentPage() {
  const authUserId = useAuthUserId();
  return <AccountAgentPage key={`agent:${authUserId ?? 'anonymous'}`} />;
}

function AccountAgentPage() {
  const { messages, isStreaming, sessionId, progress, sendMessage, stopStreaming, newSession } =
    useAgentChat();

  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 자동 스크롤
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, isStreaming]);

  // 입력 포커스
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = useCallback(() => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput('');
  }, [input, isStreaming, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* 헤더 */}
      <header className="flex items-center gap-3 px-4 md:px-6 h-14 border-b border-border/60 shrink-0 bg-card/80 backdrop-blur-sm">
        <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="size-5" />
        </Link>
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center size-8 rounded-full bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400">
            <Bot className="size-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold">AI 에이전트</h1>
            <p className="text-[11px] text-muted-foreground leading-none">
              {isStreaming
                ? progress
                  ? `처리 중... (${progress.iteration}/${progress.total})`
                  : '응답 생성 중...'
                : sessionId
                  ? '대화 진행 중'
                  : '새 대화'}
            </p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {sessionId && (
            <Button variant="ghost" size="sm" onClick={newSession} className="text-xs gap-1.5">
              <Plus className="size-3.5" />
              새 대화
            </Button>
          )}
        </div>
      </header>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-hidden">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 px-4">
            <div className="flex items-center justify-center size-16 rounded-2xl bg-primary/5 dark:bg-primary/10">
              <Bot className="size-8 text-primary/60" />
            </div>
            <div className="text-center space-y-1.5">
              <h2 className="text-lg font-semibold text-foreground">AI 에이전트</h2>
              <p className="text-sm text-muted-foreground max-w-sm">
                콘텐츠 생성, 분석, 편집 등 다양한 작업을 요청하세요.
                <br />
                도구를 자동으로 활용하여 결과를 제공합니다.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => {
                    setInput(prompt);
                    inputRef.current?.focus();
                  }}
                  className={cn(
                    'text-xs px-3 py-1.5 rounded-full border border-border/60',
                    'bg-muted/30 text-muted-foreground hover:text-foreground hover:bg-muted/60',
                    'transition-colors',
                  )}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div ref={scrollRef} className="h-full overflow-y-auto">
              <div className="max-w-3xl mx-auto divide-y divide-border/30">
                {messages.map((msg) => (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    isStreaming={isStreaming && msg.id === messages[messages.length - 1]?.id}
                  />
                ))}
              </div>
              {/* 스크롤 여백 */}
              <div className="h-4" />
            </div>
          </ScrollArea>
        )}
      </div>

      {/* 입력 영역 */}
      <div className="shrink-0 border-t border-border/60 bg-card/80 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 md:px-6 py-3">
          <div
            className={cn(
              'flex items-end gap-2 rounded-xl border border-border/60 bg-background',
              'px-3 py-2 shadow-sm',
              'focus-within:border-primary/40 focus-within:ring-2 focus-within:ring-primary/10',
              'transition-all',
            )}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요..."
              rows={1}
              className={cn(
                'flex-1 resize-none bg-transparent text-sm text-foreground',
                'placeholder:text-muted-foreground/60',
                'outline-none min-h-[24px] max-h-[160px]',
                'py-0.5',
              )}
              style={{
                height: 'auto',
                overflow: input.split('\n').length > 6 ? 'auto' : 'hidden',
              }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = 'auto';
                el.style.height = Math.min(el.scrollHeight, 160) + 'px';
              }}
              disabled={isStreaming}
            />
            {isStreaming ? (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={stopStreaming}
                className="text-destructive hover:text-destructive shrink-0"
              >
                <Square className="size-4" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleSubmit}
                disabled={!input.trim()}
                className={cn(
                  'shrink-0 transition-colors',
                  input.trim() ? 'text-primary hover:text-primary' : 'text-muted-foreground',
                )}
              >
                <Send className="size-4" />
              </Button>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground/60 text-center mt-1.5">
            Shift+Enter로 줄바꿈 / Enter로 전송
          </p>
        </div>
      </div>
    </div>
  );
}

const QUICK_PROMPTS = [
  '학습 노트 만들어줘',
  '핵심 요약해줘',
  '복습 질문 만들어줘',
  '리텐션 카드로 바꿔줘',
];

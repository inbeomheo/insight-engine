'use client';

import { Bot, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '../hooks/useAgentChat';
import ToolProgress from './ToolProgress';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export default function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex gap-3 py-4 px-4 md:px-6', isUser && 'bg-muted/30 dark:bg-muted/10')}>
      {/* 아바타 */}
      <div
        className={cn(
          'flex items-center justify-center size-8 rounded-full shrink-0 mt-0.5',
          isUser
            ? 'bg-primary/10 text-primary dark:bg-primary/20'
            : 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400',
        )}
      >
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </div>

      {/* 본문 */}
      <div className="flex-1 min-w-0 space-y-1">
        <p className="text-xs font-medium text-muted-foreground">
          {isUser ? '나' : 'AI 에이전트'}
        </p>

        {/* 도구 실행 표시 */}
        {!isUser && message.tools && message.tools.length > 0 && (
          <ToolProgress tools={message.tools} />
        )}

        {/* 메시지 내용 */}
        {message.content ? (
          <div
            className="prose prose-sm max-w-none text-foreground/90 dark:text-foreground/85 break-words"
            dangerouslySetInnerHTML={{
              __html: formatContent(message.content),
            }}
          />
        ) : (
          !isUser &&
          isStreaming && (
            <div className="flex items-center gap-1.5 py-2">
              <span className="size-1.5 rounded-full bg-primary/60 animate-pulse" />
              <span className="size-1.5 rounded-full bg-primary/60 animate-pulse [animation-delay:150ms]" />
              <span className="size-1.5 rounded-full bg-primary/60 animate-pulse [animation-delay:300ms]" />
            </div>
          )
        )}
      </div>
    </div>
  );
}

/** 마크다운 텍스트를 간단한 HTML로 변환 (경량) */
function formatContent(text: string): string {
  return text
    // 코드 블록
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-muted/50 dark:bg-muted/30 rounded-md p-3 my-2 overflow-x-auto text-xs font-mono"><code>$2</code></pre>')
    // 인라인 코드
    .replace(/`([^`]+)`/g, '<code class="bg-muted/50 dark:bg-muted/30 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>')
    // 볼드
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // 이탤릭
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 헤딩
    .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold mt-4 mb-2">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold mt-5 mb-2">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mt-6 mb-3">$1</h1>')
    // 리스트
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 list-decimal">$2</li>')
    // 줄바꿈
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>');
}

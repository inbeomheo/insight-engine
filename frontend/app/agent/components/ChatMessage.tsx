'use client';

import { Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
          <div className="prose prose-sm max-w-none text-foreground/90 dark:text-foreground/85 break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                pre: ({ children }) => (
                  <pre className="my-2 overflow-x-auto rounded-md bg-muted/50 p-3 text-xs dark:bg-muted/30">
                    {children}
                  </pre>
                ),
                code: ({ children }) => (
                  <code className="rounded bg-muted/50 px-1.5 py-0.5 font-mono text-xs dark:bg-muted/30">
                    {children}
                  </code>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
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

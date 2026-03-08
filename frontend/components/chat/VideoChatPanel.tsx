'use client';

import { useEffect, useRef, useState } from 'react';
import { MessageSquare, Send, X, ChevronDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import {
  askVideoQuestion,
  type VideoQaMessage,
  type VideoQaSource,
} from '@/lib/api';

interface VideoChatPanelProps {
  videoUrl: string;
  videoTitle?: string;
  onClose: () => void;
}

interface ChatMessage extends VideoQaMessage {
  sources?: VideoQaSource[];
}

export default function VideoChatPanel({
  videoUrl,
  videoTitle,
  onClose,
}: VideoChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSources, setShowSources] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // 새 메시지가 추가될 때마다 스크롤 아래로
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 패널 열릴 때 입력창에 포커스
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // API에 보낼 히스토리 (사용자/어시스턴트 메시지만)
    const history: VideoQaMessage[] = messages.map(({ role, content }) => ({
      role,
      content,
    }));

    try {
      const res = await askVideoQuestion(videoUrl, question, history);
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.answer,
        sources: res.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const message = err instanceof Error ? err.message : '오류가 발생했습니다.';
      toast.error(message);
      // 실패한 사용자 메시지 제거
      setMessages((prev) => prev.slice(0, -1));
      setInput(question);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Shift+Enter: 줄바꿈, Enter: 전송
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex flex-col w-full max-w-md bg-background border-l border-border shadow-2xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/40">
        <div className="flex items-center gap-2 min-w-0">
          <MessageSquare className="h-4 w-4 shrink-0 text-primary" />
          <div className="min-w-0">
            <p className="text-sm font-semibold truncate">영상에 질문하기</p>
            {videoTitle && (
              <p className="text-xs text-muted-foreground truncate">{videoTitle}</p>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 shrink-0"
          onClick={onClose}
          aria-label="영상 채팅 패널 닫기"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* 메시지 목록 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center text-muted-foreground">
            <MessageSquare className="h-10 w-10 opacity-30" />
            <p className="text-sm">
              이 영상의 내용에 대해 자유롭게 질문해보세요.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-tr-sm'
                  : 'bg-muted text-foreground rounded-tl-sm'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* 소스 인용 (어시스턴트 메시지만) */}
              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/40">
                  <button
                    type="button"
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                    onClick={() => setShowSources(showSources === idx ? null : idx)}
                    aria-label={showSources === idx ? '자막 근거 접기' : '자막 근거 펼치기'}
                  >
                    <ChevronDown
                      className={`h-3 w-3 transition-transform ${
                        showSources === idx ? 'rotate-180' : ''
                      }`}
                    />
                    자막 근거 {msg.sources.length}개
                  </button>

                  {showSources === idx && (
                    <div className="mt-2 space-y-1.5">
                      {msg.sources.map((src, sIdx) => (
                        <div
                          key={sIdx}
                          className="text-xs bg-background/60 rounded-lg px-2.5 py-1.5 border border-border/50"
                        >
                          <span className="text-muted-foreground">
                            관련도 {Math.round(src.relevance * 100)}%
                          </span>
                          <p className="mt-0.5 text-foreground/80 line-clamp-3">
                            {src.text}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* 입력 영역 */}
      <div className="px-4 py-3 border-t border-border bg-muted/20">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="질문을 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
            className="flex-1 resize-none rounded-xl border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 min-h-[2.75rem] max-h-32"
            rows={1}
            disabled={loading}
            maxLength={500}
          />
          <Button
            size="icon"
            className="h-11 w-11 shrink-0 rounded-xl"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            aria-label="질문 전송"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-1.5 text-right">
          {input.length}/500
        </p>
      </div>
    </div>
  );
}

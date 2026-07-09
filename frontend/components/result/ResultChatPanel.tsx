'use client';

import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';
import { Bot, ChevronDown, ChevronUp, Copy, Loader2, Send, User } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { askResultChat, type ResultChatMessage, type ResultChatSource } from '@/lib/api';
import { buildResultChatStudyCardMarkdown } from '@/lib/result-chat-study-card';

interface ResultChatPanelProps {
  context: string;
  model?: string;
  language?: string;
  title?: string;
  emptyText?: string;
  placeholder?: string;
  suggestedQuestions?: string[];
  studyCardTitle?: string;
}

interface ChatMessage extends ResultChatMessage {
  rag_sources?: ResultChatSource[];
}

const MAX_CONTEXT_CHARS = 50_000;

export default function ResultChatPanel({
  context,
  model,
  language = 'ko',
  title = '콘텐츠 Q&A',
  emptyText = '궁금한 점을 물어보세요. 근거가 없으면 “자막에 없는 내용입니다”라고 답합니다.',
  placeholder = '예: 이 영상의 핵심 실행 단계는?',
  suggestedQuestions = [],
  studyCardTitle,
}: ResultChatPanelProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [studyCardCopyStatus, setStudyCardCopyStatus] = useState<{
    index: number;
    status: 'copied' | 'error';
  } | null>(null);
  const { requestContext, hasContext, isContextSliced } = useMemo(() => {
    const trimmed = context.trim();
    return {
      requestContext: trimmed.slice(0, MAX_CONTEXT_CHARS),
      hasContext: trimmed.length > 0,
      isContextSliced: trimmed.length > MAX_CONTEXT_CHARS,
    };
  }, [context]);

  useEffect(() => {
    setMessages([]);
    setInput('');
    setError(null);
    setStudyCardCopyStatus(null);
  }, [context]);

  const helperText = useMemo(() => {
    if (!hasContext) return '질문할 자막/본문이 없습니다.';
    if (isContextSliced) return '자막이 길어 앞부분 50,000자를 기준으로 답변합니다.';
    return '현재 결과의 자막/본문과 관련 지식 노트만 근거로 답합니다.';
  }, [hasContext, isContextSliced]);
  const visibleSuggestedQuestions = useMemo(
    () => suggestedQuestions.map((question) => question.trim()).filter(Boolean).slice(0, 3),
    [suggestedQuestions]
  );

  const copyStudyCard = useCallback(async (message: ChatMessage, index: number) => {
    if (typeof navigator === 'undefined' || !navigator.clipboard) {
      setStudyCardCopyStatus({ index, status: 'error' });
      return;
    }

    const question = [...messages.slice(0, index)]
      .reverse()
      .find((item) => item.role === 'user')?.content;

    try {
      await navigator.clipboard.writeText(buildResultChatStudyCardMarkdown({
        title: studyCardTitle ?? title,
        question,
        answer: message.content,
        sources: message.rag_sources,
      }));
      setStudyCardCopyStatus({ index, status: 'copied' });
    } catch {
      setStudyCardCopyStatus({ index, status: 'error' });
    }
  }, [messages, studyCardTitle, title]);

  useEffect(() => {
    if (!studyCardCopyStatus) return;
    const timer = window.setTimeout(() => setStudyCardCopyStatus(null), 2000);
    return () => window.clearTimeout(timer);
  }, [studyCardCopyStatus]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = input.trim();
    if (!question || loading) return;
    if (question.length > 500) {
      setError('[채팅 실패] 질문은 최대 500자까지 입력할 수 있습니다.');
      return;
    }
    if (!hasContext) {
      setError('[채팅 실패] 답변할 자막/본문이 없습니다.');
      return;
    }

    const history: ResultChatMessage[] = messages
      .slice(-10)
      .map(({ role, content }) => ({ role, content }));
    const userMessage: ResultChatMessage = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setError(null);
    setLoading(true);

    try {
      const result = await askResultChat({
        question,
        context: requestContext,
        history,
        model,
        language,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.answer || '답변을 받지 못했습니다.',
          rag_sources: result.rag_sources ?? (result.notes ?? []).map((note) => ({
            ...note,
            type: 'knowledge_note' as const,
          })),
        },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : '채팅 요청에 실패했습니다.';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-5 overflow-hidden rounded-lg border border-border/50 bg-muted/20">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-semibold hover:bg-muted/40"
      >
        <span className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-primary" />
          {title}
        </span>
        <span className="flex items-center gap-2 text-xs font-normal text-muted-foreground">
          {messages.length > 0 ? `${messages.length}개 메시지` : '질문하기'}
          {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </span>
      </button>

      {open && (
        <div className="border-t border-border/40 p-4">
          <p className="mb-3 text-xs text-muted-foreground">{helperText}</p>
          {visibleSuggestedQuestions.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-1.5">
              {visibleSuggestedQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => {
                    setInput(question);
                    setError(null);
                  }}
                  disabled={loading || !hasContext}
                  className="rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-xs text-primary transition-colors hover:border-primary/40 hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {question}
                </button>
              ))}
            </div>
          )}

          <div className="mb-3 max-h-72 space-y-3 overflow-y-auto rounded-md bg-background/70 p-3">
            {messages.length === 0 ? (
              <p className="py-5 text-center text-sm text-muted-foreground">
                {emptyText}
              </p>
            ) : (
              messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`flex gap-2 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.role === 'assistant' && <Bot className="mt-1 h-4 w-4 shrink-0 text-primary" />}
                  <div
                    className={`max-w-[85%] whitespace-pre-wrap rounded-md px-3 py-2 text-sm leading-6 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'border border-border/60 bg-card text-foreground'
                    }`}
                  >
                    {message.content}
                    {message.role === 'assistant' && message.rag_sources && message.rag_sources.length > 0 && (
                      <div className="mt-3 border-t border-border/50 pt-2">
                        <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                          근거 {message.rag_sources.length}개
                        </p>
                        <div className="space-y-1.5">
                          {message.rag_sources.map((source, sourceIndex) => (
                            <div
                              key={`${source.id ?? 'source'}-${sourceIndex}`}
                              className="rounded-md border border-border/50 bg-background/70 px-2.5 py-1.5 text-xs"
                            >
                              <div className="flex items-center justify-between gap-2 text-muted-foreground">
                                <span className="truncate">{source.title || '지식 노트'}</span>
                                {typeof source.score === 'number' && (
                                  <span className="shrink-0">{Math.round(source.score * 100)}%</span>
                                )}
                              </div>
                              {source.snippet && (
                                <p className="mt-1 line-clamp-2 text-foreground/80">{source.snippet}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {message.role === 'assistant' && (
                      <div className="mt-3 flex flex-wrap items-center justify-end gap-1.5 border-t border-border/50 pt-2">
                        {studyCardCopyStatus?.index === index && (
                          <span className={`text-[10px] ${
                            studyCardCopyStatus.status === 'copied' ? 'text-primary' : 'text-destructive'
                          }`}>
                            {studyCardCopyStatus.status === 'copied' ? '복사 완료' : '복사 실패'}
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={() => copyStudyCard(message, index)}
                          className="inline-flex items-center gap-1 rounded-full border border-primary/20 px-2 py-1 text-[10px] font-medium text-primary transition-colors hover:border-primary/40 hover:bg-primary/5"
                        >
                          <Copy className="h-3 w-3" />
                          복습 카드 복사
                        </button>
                      </div>
                    )}
                  </div>
                  {message.role === 'user' && <User className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />}
                </div>
              ))
            )}
            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                답변 생성 중...
              </div>
            )}
          </div>

          {error && (
            <p className="mb-3 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          <form onSubmit={handleSubmit} className="space-y-2">
            <Textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={placeholder}
              maxLength={500}
              disabled={loading || !hasContext}
              className="min-h-20 resize-y"
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-muted-foreground">{input.length}/500</span>
              <Button type="submit" size="sm" disabled={loading || !input.trim() || !hasContext}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                보내기
              </Button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

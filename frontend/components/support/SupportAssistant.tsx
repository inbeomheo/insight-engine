'use client';

import { useEffect, useRef, useState } from 'react';
import { Bot, Bug, CheckCircle2, ExternalLink, Github, Loader2, MessageSquare, Send, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  createSupportDraftPr,
  createSupportGithubIssue,
  supportChat,
  type SupportChatResponse,
  type SupportTicket,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type ChatRole = 'assistant' | 'user' | 'system';

type LocalMessage = {
  id: string;
  role: ChatRole;
  content: string;
  ticket?: SupportTicket;
  githubHandoffEnabled?: boolean;
};

const STARTER_MESSAGES = [
  '퓨전 분석이 뭐야?',
  '불편사항 접수하고 싶어',
  '모바일 화면이 이상해',
];

function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function redactDiagnostic(value: string): string {
  return value
    .replace(/(authorization|bearer|token|access_token|refresh_token|api[_-]?key|password|secret)=([^\s&]+)/gi, '$1=[REDACTED]')
    .replace(/(authorization|bearer|token|access_token|refresh_token|api[_-]?key|password|secret)(\s*[:=]\s*)([^\s,;]+)/gi, '$1$2[REDACTED]')
    .replace(/https?:\/\/[^\s]+/gi, (url) => {
      try {
        const parsed = new URL(url);
        return `${parsed.origin}${parsed.pathname}`;
      } catch {
        return '[REDACTED_URL]';
      }
    })
    .slice(0, 500);
}

function getConsoleErrors(): string[] {
  if (typeof window === 'undefined') return [];
  const existing = (window as typeof window & { __insightSupportErrors?: string[] }).__insightSupportErrors || [];
  return existing.slice(-8).map(redactDiagnostic);
}

export default function SupportAssistant() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<LocalMessage[]>([
    {
      id: 'hello',
      role: 'assistant',
      content: '인사이트 엔진 사용법이 궁금하거나 불편한 점이 있으면 말해줘. 질문은 바로 답하고, 버그/개선 요청은 GitHub 이슈로 넘길 수 있어.',
    },
  ]);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const target = window as typeof window & { __insightSupportErrors?: string[] };
    target.__insightSupportErrors = target.__insightSupportErrors || [];

    const remember = (value: string) => {
      target.__insightSupportErrors = [...(target.__insightSupportErrors || []), value].slice(-20);
    };
    const onError = (event: ErrorEvent) => remember(`${event.message} @ ${event.filename}:${event.lineno}`);
    const onUnhandled = (event: PromiseRejectionEvent) => remember(`Unhandled rejection: ${String(event.reason)}`);

    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onUnhandled);
    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onUnhandled);
    };
  }, []);

  async function sendMessage(text?: string, mode: 'auto' | 'question' | 'feedback' | 'bug' | 'feature' = 'auto') {
    const message = (text ?? input).trim();
    if (!message || loading) return;

    const userMessage: LocalMessage = { id: uid(), role: 'user', content: message };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res: SupportChatResponse = await supportChat({
        message,
        mode,
        route: typeof window !== 'undefined' ? window.location.pathname : '/',
        viewport: typeof window !== 'undefined' ? { width: window.innerWidth, height: window.innerHeight } : undefined,
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
        console_errors: getConsoleErrors(),
      });
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'assistant',
          content: res.reply,
          ticket: res.ticket,
          githubHandoffEnabled: Boolean(res.github?.configured && res.github?.handoff_enabled),
        },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '지원 요청 처리 중 오류가 발생했어.';
      toast.error(msg);
      setMessages((prev) => [...prev, { id: uid(), role: 'assistant', content: msg }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  async function handleCreateIssue(ticket: SupportTicket) {
    try {
      setLoading(true);
      const res = await createSupportGithubIssue(ticket.id);
      const updated = res.ticket;
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'assistant',
          content: updated.github_issue_url
            ? `GitHub 이슈 #${updated.github_issue_number ?? ''}로 올렸어. 이제 별도 작업 에이전트가 needs-agent 큐에서 가져갈 수 있어.`
            : res.message || 'GitHub 이슈 handoff 요청을 접수했어. 티켓은 서버 큐에 저장됐고 별도 작업 에이전트가 이어받을 수 있어.',
          ticket: updated,
          githubHandoffEnabled: Boolean(updated.github_issue_url),
        },
      ]);
      toast.success(updated.github_issue_url ? 'GitHub 이슈를 생성했어' : 'GitHub 이슈 요청을 접수했어');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'GitHub 이슈 생성에 실패했어.';
      toast.error(msg);
      setMessages((prev) => [...prev, { id: uid(), role: 'assistant', content: msg }]);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateDraftPr(ticket: SupportTicket) {
    try {
      setLoading(true);
      const res = await createSupportDraftPr(ticket.id);
      const updated = res.ticket;
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: 'assistant',
          content: updated.github_pr_url
            ? `docs-only Draft PR #${updated.github_pr_number ?? ''}을 만들었어. 코드 수정은 하지 않았고, 작업 에이전트가 이어받을 스펙만 담았어.`
            : res.message || 'Draft PR handoff 요청을 접수했어. 티켓은 서버 큐에 저장됐고 별도 작업 에이전트가 이어받을 수 있어.',
          ticket: updated,
          githubHandoffEnabled: Boolean(updated.github_pr_url),
        },
      ]);
      toast.success(updated.github_pr_url ? 'Draft PR을 생성했어' : 'Draft PR 요청을 접수했어');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Draft PR 생성에 실패했어.';
      toast.error(msg);
      setMessages((prev) => [...prev, { id: uid(), role: 'assistant', content: msg }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <>
      <Button
        type="button"
        className={cn(
          'fixed bottom-6 right-6 z-[70] hidden h-12 rounded-full border border-foreground bg-primary px-4 text-sm font-black text-primary-foreground shadow-[4px_4px_0_#17150F] transition-transform active:scale-[0.96] xl:flex',
          'hover:bg-primary/95',
        )}
        onClick={() => setOpen(true)}
        aria-label="도움말/피드백 열기"
      >
        <Bot className="h-4 w-4" />
        <span className="hidden xl:inline">도움말/피드백</span>
      </Button>

      {open && (
        <div className="fixed inset-0 z-[80] flex items-end justify-end bg-foreground/18 p-3 backdrop-blur-[1px] sm:p-5">
          <section className="flex h-[min(720px,calc(100dvh-2rem))] w-full max-w-[430px] flex-col overflow-hidden border border-foreground bg-background shadow-[8px_8px_0_#17150F]">
            <header className="flex items-center justify-between border-b border-border bg-card px-4 py-3">
              <div className="flex min-w-0 items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-sm bg-foreground text-background">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <h2 className="text-sm font-black tracking-[-0.02em]">Support Assistant</h2>
                  <p className="text-xs text-muted-foreground">질문 답변 · 불편 접수 · GitHub handoff</p>
                </div>
              </div>
              <Button variant="ghost" size="icon-sm" onClick={() => setOpen(false)} aria-label="지원 패널 닫기">
                <X className="h-4 w-4" />
              </Button>
            </header>

            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {messages.map((message) => (
                <div key={message.id} className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}>
                  <div
                    className={cn(
                      'max-w-[88%] border px-3 py-2 text-sm leading-6',
                      message.role === 'user'
                        ? 'border-foreground bg-foreground text-background'
                        : 'border-border bg-card text-foreground',
                    )}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    {message.ticket && (
                      <TicketActions
                        ticket={message.ticket}
                        disabled={loading}
                        githubHandoffEnabled={message.githubHandoffEnabled}
                        onCreateIssue={handleCreateIssue}
                        onCreateDraftPr={handleCreateDraftPr}
                      />
                    )}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="border border-border bg-card px-3 py-2 text-sm text-muted-foreground">
                    <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> 처리 중...
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-border bg-card/60 px-4 py-3">
              <div className="mb-2 flex flex-wrap gap-1.5">
                {STARTER_MESSAGES.map((starter) => (
                  <button
                    key={starter}
                    type="button"
                    className="rounded-full border border-border bg-background px-3 py-1 text-[11px] font-semibold text-muted-foreground hover:border-foreground/50 hover:text-foreground"
                    onClick={() => sendMessage(starter)}
                    disabled={loading}
                  >
                    {starter}
                  </button>
                ))}
              </div>
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="기능 질문이나 불편사항을 입력해줘..."
                  className="min-h-11 max-h-28 flex-1 resize-none border border-border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground/50 focus:border-foreground"
                  rows={2}
                  maxLength={1000}
                  disabled={loading}
                />
                <Button
                  type="button"
                  size="icon"
                  className="h-11 w-11 rounded-sm"
                  onClick={() => sendMessage()}
                  disabled={!input.trim() || loading}
                  aria-label="지원 메시지 전송"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function TicketActions({
  ticket,
  disabled,
  githubHandoffEnabled,
  onCreateIssue,
  onCreateDraftPr,
}: {
  ticket: SupportTicket;
  disabled: boolean;
  githubHandoffEnabled?: boolean;
  onCreateIssue: (ticket: SupportTicket) => void;
  onCreateDraftPr: (ticket: SupportTicket) => void;
}) {
  const issueRequested = ticket.status === 'issue_requested' || Boolean(ticket.github_issue_url);
  const draftPrRequested = ticket.status === 'draft_pr_requested' || Boolean(ticket.github_pr_url);

  return (
    <div className="mt-3 border-t border-border/70 pt-2">
      <div className="mb-2 flex flex-wrap items-center gap-1.5 text-[11px]">
        <span className="inline-flex items-center gap-1 border border-border bg-background px-2 py-0.5 font-bold">
          <Bug className="h-3 w-3" /> {ticket.kind}
        </span>
        <span className="border border-border bg-background px-2 py-0.5 font-bold">{ticket.severity}</span>
        {ticket.github_issue_url && <StatusLink href={ticket.github_issue_url} label={`Issue #${ticket.github_issue_number ?? ''}`} />}
        {ticket.github_pr_url && <StatusLink href={ticket.github_pr_url} label={`PR #${ticket.github_pr_number ?? ''}`} />}
      </div>
      {ticket.related_files && ticket.related_files.length > 0 && (
        <p className="mb-2 line-clamp-2 text-[11px] text-muted-foreground">
          후보: {ticket.related_files.join(', ')}
        </p>
      )}
      {!githubHandoffEnabled && !ticket.github_issue_url && !ticket.github_pr_url && (
        <p className="mb-2 text-[11px] text-muted-foreground">
          접수된 티켓은 서버에 저장됐어. 버튼을 누르면 GitHub handoff 요청을 큐에 넣어둘게.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="xs"
          variant="outline"
          onClick={() => onCreateIssue(ticket)}
          disabled={disabled || issueRequested}
        >
          {issueRequested ? <CheckCircle2 className="h-3 w-3" /> : <Github className="h-3 w-3" />}
          {ticket.github_issue_url ? '이슈 완료' : ticket.status === 'issue_requested' ? '이슈 요청됨' : githubHandoffEnabled ? '이슈 올리기' : '이슈 요청'}
        </Button>
        <Button
          type="button"
          size="xs"
          variant="outline"
          onClick={() => onCreateDraftPr(ticket)}
          disabled={disabled || draftPrRequested}
        >
          {draftPrRequested ? <CheckCircle2 className="h-3 w-3" /> : <MessageSquare className="h-3 w-3" />}
          {ticket.github_pr_url ? 'PR 완료' : ticket.status === 'draft_pr_requested' ? 'PR 요청됨' : githubHandoffEnabled ? 'Draft PR' : 'PR 요청'}
        </Button>
      </div>
    </div>
  );
}

function StatusLink({ href, label }: { href: string; label: string }) {
  return (
    <a
      className="inline-flex items-center gap-1 border border-border bg-background px-2 py-0.5 font-bold text-primary hover:underline"
      href={href}
      target="_blank"
      rel="noreferrer"
    >
      {label}
      <ExternalLink className="h-3 w-3" />
    </a>
  );
}

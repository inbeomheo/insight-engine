'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiUrl, createIdempotencyKey } from '@/lib/api';
import { authFetch, getAuthSession } from '@/lib/auth-session';
import { useAuthUserId } from '@/hooks/useAuthUserId';

// ── 타입 ──

export interface ToolExecution {
  name: string;
  args?: Record<string, unknown>;
  startedAt: number;
  elapsed?: number;
  done: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tools?: ToolExecution[];
  createdAt: number;
}

export interface AgentStats {
  total_tokens?: number;
  elapsed?: number;
  iterations?: number;
}

interface SSEEvent {
  type: 'delta' | 'tool_start' | 'tool_end' | 'progress' | 'done' | 'error';
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  elapsed?: number;
  iteration?: number;
  total?: number;
  session_id?: string;
  stats?: AgentStats;
  error?: string;
}

// ── 훅 ──

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ iteration: number; total: number } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const requestEpochRef = useRef(0);
  const authUserId = useAuthUserId();

  useEffect(() => {
    requestEpochRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;

    // 이전 계정의 대화와 세션을 새 계정에 인계하지 않는다.
    setMessages([]);
    setSessionId(null);
    setIsStreaming(false);
    setProgress(null);

    return () => {
      requestEpochRef.current += 1;
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, [authUserId]);

  const sendMessage = useCallback(
    async (text: string, toolsets: string[] = ['role_writer']) => {
      if (!text.trim() || isStreaming) return;

      const requestUserId = authUserId;
      const controller = new AbortController();
      const requestEpoch = requestEpochRef.current + 1;
      requestEpochRef.current = requestEpoch;
      abortRef.current?.abort();
      abortRef.current = controller;

      const isRequestContextCurrent = () =>
        requestEpochRef.current === requestEpoch
        && (getAuthSession()?.user.id ?? null) === requestUserId;
      const ownsRequest = () =>
        isRequestContextCurrent() && abortRef.current === controller;
      const canApplyEvent = () => ownsRequest() && !controller.signal.aborted;

      // 사용자 메시지 추가
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: text.trim(),
        createdAt: Date.now(),
      };

      // 어시스턴트 메시지 준비 (스트리밍용)
      const assistantId = crypto.randomUUID();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        tools: [],
        createdAt: Date.now(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      setProgress(null);

      try {
        const res = await authFetch(apiUrl('/api/agent/chat/stream'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': createIdempotencyKey(),
          },
          body: JSON.stringify({
            message: text.trim(),
            session_id: sessionId,
            toolsets,
          }),
          signal: controller.signal,
        });

        if (!canApplyEvent()) return;

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          if (!canApplyEvent()) return;
          throw new Error(body.error || `HTTP ${res.status}`);
        }

        if (!res.body) throw new Error('응답 스트림이 없습니다.');
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (!canApplyEvent()) {
            await reader.cancel().catch(() => undefined);
            return;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            let event: SSEEvent;
            try {
              event = JSON.parse(line.slice(6));
            } catch {
              continue;
            }
            if (!canApplyEvent()) return;

            switch (event.type) {
              case 'delta':
                setMessages((prev) =>
                  isRequestContextCurrent()
                    ? prev.map((m) =>
                        m.id === assistantId
                          ? { ...m, content: m.content + (event.content ?? '') }
                          : m,
                      )
                    : prev,
                );
                break;

              case 'tool_start':
                setMessages((prev) =>
                  isRequestContextCurrent()
                    ? prev.map((m) =>
                        m.id === assistantId
                          ? {
                              ...m,
                              tools: [
                                ...(m.tools ?? []),
                                {
                                  name: event.name ?? 'unknown',
                                  args: event.args,
                                  startedAt: Date.now(),
                                  done: false,
                                },
                              ],
                            }
                          : m,
                      )
                    : prev,
                );
                break;

              case 'tool_end':
                setMessages((prev) =>
                  isRequestContextCurrent()
                    ? prev.map((m) => {
                        if (m.id !== assistantId) return m;
                        const tools = (m.tools ?? []).map((t) =>
                          t.name === event.name && !t.done
                            ? { ...t, elapsed: event.elapsed, done: true }
                            : t,
                        );
                        return { ...m, tools };
                      })
                    : prev,
                );
                break;

              case 'progress':
                setProgress((current) => isRequestContextCurrent()
                  ? {
                      iteration: event.iteration ?? 0,
                      total: event.total ?? 0,
                    }
                  : current);
                break;

              case 'done':
                if (event.session_id) {
                  setSessionId((current) => isRequestContextCurrent() ? event.session_id! : current);
                }
                break;

              case 'error':
                setMessages((prev) =>
                  isRequestContextCurrent()
                    ? prev.map((m) =>
                        m.id === assistantId
                          ? { ...m, content: m.content || `오류: ${event.error ?? '알 수 없는 오류'}` }
                          : m,
                      )
                    : prev,
                );
                break;
            }
          }
        }
      } catch (err) {
        if ((err as DOMException)?.name === 'AbortError' || !canApplyEvent()) return;
        setMessages((prev) =>
          isRequestContextCurrent()
            ? prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content || `연결 오류: ${(err as Error).message}` }
                  : m,
              )
            : prev,
        );
      } finally {
        if (ownsRequest()) {
          setIsStreaming(false);
          setProgress(null);
          abortRef.current = null;
        }
      }
    },
    [authUserId, isStreaming, sessionId],
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const newSession = useCallback(() => {
    requestEpochRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([]);
    setSessionId(null);
    setIsStreaming(false);
    setProgress(null);
  }, []);

  return {
    messages,
    isStreaming,
    sessionId,
    progress,
    sendMessage,
    stopStreaming,
    newSession,
  };
}

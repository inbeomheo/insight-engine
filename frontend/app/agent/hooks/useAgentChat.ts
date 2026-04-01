'use client';

import { useCallback, useRef, useState } from 'react';
import { apiUrl } from '@/lib/api';

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

  const sendMessage = useCallback(
    async (text: string, toolsets: string[] = ['role_writer']) => {
      if (!text.trim() || isStreaming) return;

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

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const res = await fetch(apiUrl('/api/agent/chat/stream'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text.trim(),
            session_id: sessionId,
            toolsets,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.error || `HTTP ${res.status}`);
        }

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

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

            switch (event.type) {
              case 'delta':
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: m.content + (event.content ?? '') }
                      : m,
                  ),
                );
                break;

              case 'tool_start':
                setMessages((prev) =>
                  prev.map((m) =>
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
                  ),
                );
                break;

              case 'tool_end':
                setMessages((prev) =>
                  prev.map((m) => {
                    if (m.id !== assistantId) return m;
                    const tools = (m.tools ?? []).map((t) =>
                      t.name === event.name && !t.done
                        ? { ...t, elapsed: event.elapsed, done: true }
                        : t,
                    );
                    return { ...m, tools };
                  }),
                );
                break;

              case 'progress':
                setProgress({
                  iteration: event.iteration ?? 0,
                  total: event.total ?? 0,
                });
                break;

              case 'done':
                if (event.session_id) {
                  setSessionId(event.session_id);
                }
                break;

              case 'error':
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, content: m.content || `오류: ${event.error ?? '알 수 없는 오류'}` }
                      : m,
                  ),
                );
                break;
            }
          }
        }
      } catch (err) {
        if ((err as DOMException)?.name === 'AbortError') return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: m.content || `연결 오류: ${(err as Error).message}` }
              : m,
          ),
        );
      } finally {
        setIsStreaming(false);
        setProgress(null);
        abortRef.current = null;
      }
    },
    [isStreaming, sessionId],
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const newSession = useCallback(() => {
    abortRef.current?.abort();
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

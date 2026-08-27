import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import { useAgentChat } from './useAgentChat';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

type AgentChatHook = ReturnType<typeof useAgentChat>;

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function controlledSse() {
  const encoder = new TextEncoder();
  let streamController!: ReadableStreamDefaultController<Uint8Array>;
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      streamController = controller;
    },
  });

  return {
    response: new Response(stream, {
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
    }),
    emit(event: Record<string, unknown>) {
      streamController.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
    },
    close() {
      streamController.close();
    },
  };
}

let currentHook: AgentChatHook | null = null;

function Harness() {
  const hook = useAgentChat();
  useEffect(() => {
    currentHook = hook;
  }, [hook]);
  return null;
}

describe('useAgentChat 계정 격리', () => {
  let container: HTMLDivElement;
  let root: Root;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setAuthSession(null);
    localStorage.clear();
    currentHook = null;
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    setAuthSession(null);
    container.remove();
    currentHook = null;
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('A SSE를 중단·초기화하고 stale 이벤트와 finally가 B 대화를 덮어쓰지 못하게 한다', async () => {
    const streamA = controlledSse();
    const streamB = controlledSse();
    const signals: AbortSignal[] = [];
    fetchMock
      .mockImplementationOnce((_input: RequestInfo | URL, init?: RequestInit) => {
        signals.push(init?.signal as AbortSignal);
        return Promise.resolve(streamA.response);
      })
      .mockImplementationOnce((_input: RequestInfo | URL, init?: RequestInit) => {
        signals.push(init?.signal as AbortSignal);
        return Promise.resolve(streamB.response);
      });
    setAuthSession(authSession('account-a'));

    await act(async () => root.render(<Harness />));
    let requestA!: Promise<void>;
    await act(async () => {
      requestA = currentHook!.sendMessage('A 질문');
      await Promise.resolve();
    });
    await vi.waitFor(() => expect(currentHook?.isStreaming).toBe(true));
    expect(currentHook?.messages.map((message) => message.content)).toContain('A 질문');

    await act(async () => setAuthSession(authSession('account-b')));
    await vi.waitFor(() => {
      expect(currentHook?.messages).toEqual([]);
      expect(currentHook?.isStreaming).toBe(false);
    });
    expect(signals[0].aborted).toBe(true);

    let requestB!: Promise<void>;
    await act(async () => {
      requestB = currentHook!.sendMessage('B 질문');
      await Promise.resolve();
    });
    await vi.waitFor(() => expect(currentHook?.isStreaming).toBe(true));

    await act(async () => {
      streamA.emit({ type: 'delta', content: 'A의 늦은 응답' });
      await requestA;
    });
    expect(currentHook?.isStreaming).toBe(true);
    expect(currentHook?.messages.map((message) => message.content)).toContain('B 질문');
    expect(currentHook?.messages.some((message) => message.content.includes('A의 늦은 응답'))).toBe(false);

    await act(async () => {
      streamB.emit({ type: 'delta', content: 'B의 응답' });
      streamB.emit({ type: 'done', session_id: 'session-b' });
      streamB.close();
      await requestB;
    });
    await vi.waitFor(() => {
      expect(currentHook?.isStreaming).toBe(false);
      expect(currentHook?.sessionId).toBe('session-b');
      expect(currentHook?.messages.some((message) => message.content === 'B의 응답')).toBe(true);
    });
  });
});

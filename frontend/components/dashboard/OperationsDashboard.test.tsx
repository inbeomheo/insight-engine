import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import OperationsDashboard from './OperationsDashboard';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const { authFetchMock } = vi.hoisted(() => ({ authFetchMock: vi.fn() }));

vi.mock('@/lib/auth-session', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/auth-session')>();
  return { ...actual, authFetch: authFetchMock };
});

vi.mock('@/lib/api', () => ({
  apiUrl: (path: string) => `https://api.example.test${path}`,
}));

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function dashboardResponse(totalGenerations: number): Response {
  return new Response(JSON.stringify({
    total_generations: totalGenerations,
    success_rate: 100,
    avg_time: 1,
    style_distribution: {},
    daily_usage: [],
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('OperationsDashboard 계정 격리', () => {
  let container: HTMLDivElement;
  let root: Root | null;

  beforeEach(() => {
    setAuthSession(null);
    localStorage.clear();
    authFetchMock.mockReset();
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    setAuthSession(null);
    container.remove();
    vi.clearAllMocks();
  });

  it('A 요청을 중단하고 늦게 온 A 응답을 B 대시보드에 반영하지 않는다', async () => {
    const pendingA = deferred<Response>();
    const pendingB = deferred<Response>();
    authFetchMock
      .mockImplementationOnce(() => pendingA.promise)
      .mockImplementationOnce(() => pendingB.promise);
    setAuthSession(authSession('account-a'));

    await act(async () => root!.render(<OperationsDashboard />));
    await vi.waitFor(() => expect(authFetchMock).toHaveBeenCalledTimes(1));
    const signalA = authFetchMock.mock.calls[0][1]?.signal as AbortSignal;

    await act(async () => setAuthSession(authSession('account-b')));
    await vi.waitFor(() => expect(authFetchMock).toHaveBeenCalledTimes(2));
    expect(signalA.aborted).toBe(true);

    await act(async () => {
      pendingB.resolve(dashboardResponse(22));
      await Promise.resolve();
    });
    await vi.waitFor(() => expect(container.textContent).toContain('22'));

    await act(async () => {
      pendingA.resolve(dashboardResponse(11));
      await Promise.resolve();
    });
    expect(container.textContent).toContain('22');
    expect(container.textContent).not.toContain('11');
  });

  it('언마운트 시 진행 중인 대시보드 요청을 중단한다', async () => {
    const pending = deferred<Response>();
    authFetchMock.mockImplementationOnce(() => pending.promise);
    setAuthSession(authSession('account-a'));

    await act(async () => root!.render(<OperationsDashboard />));
    await vi.waitFor(() => expect(authFetchMock).toHaveBeenCalledTimes(1));
    const signal = authFetchMock.mock.calls[0][1]?.signal as AbortSignal;

    await act(async () => root!.unmount());
    root = null;
    expect(signal.aborted).toBe(true);

    pending.resolve(dashboardResponse(99));
    await Promise.resolve();
  });
});

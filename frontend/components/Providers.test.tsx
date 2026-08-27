import { act, useEffect, type PropsWithChildren } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Providers, { protectedAuthMeta, useAuthScope } from './Providers';
import {
  AUTH_SESSION_STORAGE_KEY,
  setAuthSession,
  type AuthSession,
} from '@/lib/auth-session';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

vi.mock('next-themes', () => ({
  ThemeProvider: ({ children }: PropsWithChildren) => children,
}));
vi.mock('@/lib/i18n/I18nProvider', () => ({
  I18nProvider: ({ children }: PropsWithChildren) => children,
}));
vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: PropsWithChildren) => children,
}));
vi.mock('@/components/ui/sonner', () => ({ Toaster: () => null }));

const AUTH_A: AuthSession = {
  user: { id: 'account-a' },
  session: { access_token: 'token-a' },
};
const AUTH_B: AuthSession = {
  user: { id: 'account-b' },
  session: { access_token: 'token-b' },
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

let observedClient: QueryClient | null = null;

function ProtectedProbe({
  load,
  onClient,
}: {
  load: (authScope: string) => Promise<string>;
  onClient: (queryClient: QueryClient) => void;
}) {
  const authScope = useAuthScope();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['protected', authScope, 'probe'],
    queryFn: () => load(authScope),
    meta: protectedAuthMeta(authScope),
    retry: false,
  });

  useEffect(() => onClient(queryClient), [onClient, queryClient]);

  return <output data-auth-scope={authScope}>{query.data ?? 'loading'}</output>;
}

function captureClient(queryClient: QueryClient) {
  observedClient = queryClient;
}

describe('Providers 인증 Query 경계', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    observedClient = null;
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    vi.clearAllMocks();
  });

  it('A 캐시를 B 전환 즉시 제거하고 공개 캐시는 유지한다', async () => {
    const pendingB = deferred<string>();
    const load = vi.fn((authScope: string) =>
      authScope === 'user:account-a'
        ? Promise.resolve('A private data')
        : pendingB.promise,
    );
    setAuthSession(AUTH_A);

    await act(async () => {
      root.render(
        <Providers>
          <ProtectedProbe load={load} onClient={captureClient} />
        </Providers>,
      );
    });
    await vi.waitFor(() => expect(container.textContent).toBe('A private data'));
    observedClient!.setQueryData(['public', 'providers'], 'public data');

    await act(async () => {
      setAuthSession(AUTH_B);
    });

    expect(observedClient!.getQueryData([
      'protected',
      'user:account-a',
      'probe',
    ])).toBeUndefined();
    expect(observedClient!.getQueryData(['public', 'providers'])).toBe('public data');
    expect(container.textContent).toBe('loading');

    pendingB.resolve('B private data');
    await vi.waitFor(() => expect(container.textContent).toBe('B private data'));
  });

  it('A의 느지막한 응답이 B 캐시나 화면을 다시 채우지 못한다', async () => {
    const pendingA = deferred<string>();
    const pendingB = deferred<string>();
    const load = vi.fn((authScope: string) =>
      authScope === 'user:account-a' ? pendingA.promise : pendingB.promise,
    );
    setAuthSession(AUTH_A);

    await act(async () => {
      root.render(
        <Providers>
          <ProtectedProbe load={load} onClient={captureClient} />
        </Providers>,
      );
    });
    await vi.waitFor(() => expect(load).toHaveBeenCalledWith('user:account-a'));

    await act(async () => {
      setAuthSession(AUTH_B);
    });
    await vi.waitFor(() => expect(load).toHaveBeenCalledWith('user:account-b'));

    pendingB.resolve('B current data');
    await vi.waitFor(() => expect(container.textContent).toBe('B current data'));

    pendingA.resolve('A late data');
    await act(async () => {
      await Promise.resolve();
    });

    expect(container.textContent).toBe('B current data');
    expect(observedClient!.getQueryData([
      'protected',
      'user:account-a',
      'probe',
    ])).toBeUndefined();
    expect(observedClient!.getQueryData([
      'protected',
      'user:account-b',
      'probe',
    ])).toBe('B current data');
  });

  it('같은 사용자의 토큰 갱신은 캐시를 유지하고 로그아웃은 제거한다', async () => {
    const pendingAnonymous = deferred<string>();
    const load = vi.fn((authScope: string) =>
      authScope === 'user:account-a'
        ? Promise.resolve('A private data')
        : pendingAnonymous.promise,
    );
    setAuthSession(AUTH_A);

    await act(async () => {
      root.render(
        <Providers>
          <ProtectedProbe load={load} onClient={captureClient} />
        </Providers>,
      );
    });
    await vi.waitFor(() => expect(container.textContent).toBe('A private data'));

    await act(async () => {
      setAuthSession({
        ...AUTH_A,
        session: { access_token: 'token-a-refreshed' },
      });
    });

    expect(container.textContent).toBe('A private data');
    expect(load).toHaveBeenCalledTimes(1);
    expect(observedClient!.getQueryData([
      'protected',
      'user:account-a',
      'probe',
    ])).toBe('A private data');

    await act(async () => {
      setAuthSession(null);
    });

    expect(observedClient!.getQueryData([
      'protected',
      'user:account-a',
      'probe',
    ])).toBeUndefined();
    expect(container.querySelector('output')?.dataset.authScope).toBe('anonymous');
    expect(container.textContent).toBe('loading');

    pendingAnonymous.resolve('anonymous data');
    await vi.waitFor(() => expect(container.textContent).toBe('anonymous data'));
  });
});

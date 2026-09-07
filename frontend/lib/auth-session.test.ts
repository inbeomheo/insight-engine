import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  AUTH_SESSION_STORAGE_KEY,
  authFetch,
  getAuthSession,
  setAuthSession,
  signIn,
  signOut,
} from './auth-session';

const INITIAL_AUTH = {
  user: { id: 'user-1', email: 'user@example.com' },
  session: {
    access_token: 'access-old',
    refresh_token: 'refresh-old',
    expires_at: 1,
  },
};

afterEach(() => {
  localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
  vi.unstubAllGlobals();
});

describe('auth session', () => {
  it('로그인 세션을 저장하고 보호 API에 Bearer 토큰을 주입한다', async () => {
    setAuthSession(INITIAL_AUTH);
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await authFetch('/api/protected', { headers: { 'X-Test': 'yes' } });

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer access-old');
    expect(headers.get('X-Test')).toBe('yes');
  });

  it('401이면 HttpOnly refresh 쿠키로 갱신하고 원 요청을 새 토큰으로 재시도한다', async () => {
    setAuthSession(INITIAL_AUTH);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: 'TOKEN_EXPIRED' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        success: true,
        user: { id: 'user-1', email: 'user@example.com' },
        session: { access_token: 'access-new', refresh_token: 'refresh-new', expires_at: 2 },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const response = await authFetch('/api/protected');

    expect(response.status).toBe(200);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/auth/refresh');
    const retryHeaders = fetchMock.mock.calls[2][1].headers as Headers;
    expect(retryHeaders.get('Authorization')).toBe('Bearer access-new');
    expect(getAuthSession()?.session.refresh_token).toBeUndefined();
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({
      credentials: 'include',
    }));
  });

  it('도메인 서비스의 일반 401은 인증 토큰 갱신으로 오인하지 않는다', async () => {
    setAuthSession(INITIAL_AUTH);
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: 'NotebookLM CLI 인증이 필요합니다.',
      code: 'NOTEBOOKLM_AUTH_REQUIRED',
    }), { status: 401, headers: { 'Content-Type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);

    const response = await authFetch('/api/notebooklm/status');

    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(getAuthSession()?.session.access_token).toBe('access-old');
  });

  it('갱신 중 다른 계정으로 로그인하면 이전 세션이 되살아나지 않는다', async () => {
    setAuthSession(INITIAL_AUTH);
    let resolveRefresh!: (response: Response) => void;
    const pendingRefresh = new Promise<Response>((resolve) => {
      resolveRefresh = resolve;
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: 'TOKEN_EXPIRED' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockReturnValueOnce(pendingRefresh);
    vi.stubGlobal('fetch', fetchMock);

    const request = authFetch('/api/protected');
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    setAuthSession({
      user: { id: 'user-2', email: 'other@example.com' },
      session: { access_token: 'access-other', refresh_token: 'refresh-other' },
    });
    resolveRefresh(new Response(JSON.stringify({
      user: { id: 'user-1', email: 'user@example.com' },
      session: { access_token: 'access-stale', refresh_token: 'refresh-stale' },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    const response = await request;

    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(getAuthSession()?.user.id).toBe('user-2');
    expect(getAuthSession()?.session.access_token).toBe('access-other');
  });

  it('갱신 뒤 재시도도 토큰 401이면 동일 세션을 폐기한다', async () => {
    setAuthSession(INITIAL_AUTH);
    const authFailure = () => new Response(JSON.stringify({ code: 'TOKEN_INVALID' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(authFailure())
      .mockResolvedValueOnce(new Response(JSON.stringify({
        user: { id: 'user-1', email: 'user@example.com' },
        session: { access_token: 'access-new', refresh_token: 'refresh-new' },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(authFailure());
    vi.stubGlobal('fetch', fetchMock);

    const response = await authFetch('/api/protected');

    expect(response.status).toBe(401);
    expect(getAuthSession()).toBeNull();
  });

  it('갱신 응답 사용자가 기대 계정과 다르면 토큰을 저장하거나 재시도하지 않는다', async () => {
    setAuthSession(INITIAL_AUTH);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: 'TOKEN_EXPIRED' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        user: { id: 'user-2', email: 'other@example.com' },
        session: { access_token: 'access-other', expires_at: 2 },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);

    const response = await authFetch('/api/protected');

    expect(response.status).toBe(401);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(getAuthSession()).toBeNull();
  });

  it('갱신과 보호 요청 재시도가 끝날 때까지 다른 탭 로그인을 직렬화한다', async () => {
    setAuthSession(INITIAL_AUTH);
    let lockTail = Promise.resolve();
    const locks = {
      request: vi.fn(<T,>(_name: string, operation: () => Promise<T>) => {
        const previous = lockTail;
        let release!: () => void;
        lockTail = new Promise<void>((resolve) => { release = resolve; });
        return previous.then(operation).finally(release);
      }),
    };
    vi.stubGlobal('navigator', { locks });

    let resolveRefresh!: (response: Response) => void;
    const pendingRefresh = new Promise<Response>((resolve) => { resolveRefresh = resolve; });
    let protectedCalls = 0;
    const callOrder: string[] = [];
    const fetchMock = vi.fn((input: string | URL) => {
      const url = String(input);
      if (url === '/api/protected') {
        protectedCalls += 1;
        callOrder.push(`protected-${protectedCalls}`);
        return Promise.resolve(protectedCalls === 1
          ? new Response(JSON.stringify({ code: 'TOKEN_EXPIRED' }), {
            status: 401,
            headers: { 'Content-Type': 'application/json' },
          })
          : new Response('{}', { status: 200 }));
      }
      if (url === '/api/auth/refresh') {
        callOrder.push('refresh');
        return pendingRefresh;
      }
      callOrder.push('login');
      return Promise.resolve(new Response(JSON.stringify({
        user: { id: 'user-2', email: 'other@example.com' },
        session: { access_token: 'access-b' },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    });
    vi.stubGlobal('fetch', fetchMock);

    const protectedRequest = authFetch('/api/protected');
    await vi.waitFor(() => expect(callOrder).toEqual(['protected-1', 'refresh']));
    const login = signIn('other@example.com', 'password');
    await Promise.resolve();
    expect(callOrder).toEqual(['protected-1', 'refresh']);

    resolveRefresh(new Response(JSON.stringify({
      user: { id: 'user-1', email: 'user@example.com' },
      session: { access_token: 'access-new', expires_at: 2 },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    await Promise.all([protectedRequest, login]);

    expect(callOrder).toEqual(['protected-1', 'refresh', 'protected-2', 'login']);
    expect(getAuthSession()?.user.id).toBe('user-2');
  });

  it('로그아웃 토큰이 만료됐으면 같은 잠금 안에서 갱신 후 서버 세션을 폐기한다', async () => {
    setAuthSession(INITIAL_AUTH);
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: 'TOKEN_EXPIRED' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        user: { id: 'user-1', email: 'user@example.com' },
        session: { access_token: 'access-new', expires_at: 2 },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }));
    vi.stubGlobal('fetch', fetchMock);

    await signOut();

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/auth/logout',
      '/api/auth/refresh',
      '/api/auth/logout',
    ]);
    expect(getAuthSession()).toBeNull();
  });

  it('로그인 응답을 이후 요청에서 재사용할 수 있게 저장한다', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      success: true,
      user: { id: 'user-2', email: 'next@example.com' },
      session: { access_token: 'access-login', refresh_token: 'refresh-login' },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    vi.stubGlobal('fetch', fetchMock);

    await signIn('next@example.com', 'password');

    expect(getAuthSession()?.user.id).toBe('user-2');
    expect(getAuthSession()?.session.access_token).toBe('access-login');
    expect(getAuthSession()?.session.refresh_token).toBeUndefined();
    expect(localStorage.getItem(AUTH_SESSION_STORAGE_KEY)).not.toContain('refresh-login');
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({
      credentials: 'include',
      headers: expect.objectContaining({ 'X-Auth-Transport': 'cookie' }),
    }));
  });
});

export interface AuthUser {
  id: string;
  email?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  expires_at?: number;
}

export interface AuthSession {
  user: AuthUser;
  session: AuthTokens;
}

const AUTH_STORAGE_KEY = 'insight-engine-auth-session';
const AUTH_EVENT = 'insight-engine-auth-change';
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

const AUTH_MUTATION_LOCK = 'insight-engine-auth-mutation';
let authMutationTail: Promise<void> = Promise.resolve();

function withoutRefreshToken(value: AuthSession): AuthSession {
  return {
    user: value.user,
    session: {
      access_token: value.session.access_token,
      ...(value.session.expires_at === undefined
        ? {}
        : { expires_at: value.session.expires_at }),
    },
  };
}

export function getAuthSession(): AuthSession | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as AuthSession;
    if (!value?.user?.id || !value?.session?.access_token) {
      return null;
    }
    return value;
  } catch {
    return null;
  }
}

export function setAuthSession(value: AuthSession | null): void {
  if (typeof window === 'undefined') return;
  if (value) {
    // refresh token은 HttpOnly 쿠키에만 둔다. 이전 서버/테스트 응답에 값이
    // 포함돼도 스크립트가 읽을 수 있는 저장소에는 access token만 남긴다.
    const safeValue = withoutRefreshToken(value);
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(safeValue));
  } else {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
  window.dispatchEvent(new Event(AUTH_EVENT));
}

export function subscribeAuthSession(listener: () => void): () => void {
  if (typeof window === 'undefined') return () => {};
  window.addEventListener(AUTH_EVENT, listener);
  window.addEventListener('storage', listener);
  return () => {
    window.removeEventListener(AUTH_EVENT, listener);
    window.removeEventListener('storage', listener);
  };
}

async function parseAuthResponse(response: Response): Promise<AuthSession> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  if (!body.user || !body.session) {
    throw new Error('인증 서버 응답이 올바르지 않습니다.');
  }
  return withoutRefreshToken({ user: body.user, session: body.session });
}

export async function signIn(email: string, password: string): Promise<AuthSession> {
  return withAuthMutationLock(async () => {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Auth-Transport': 'cookie',
      },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });
    const auth = await parseAuthResponse(response);
    setAuthSession(auth);
    return auth;
  });
}

export async function signUp(email: string, password: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  return body.message || '회원가입이 완료되었습니다.';
}

function sameRefreshIdentity(left: AuthSession | null, right: AuthSession): boolean {
  if (!left || left.user.id !== right.user.id) return false;
  if (right.session.refresh_token) {
    return left.session.refresh_token === right.session.refresh_token;
  }
  return left.session.access_token === right.session.access_token;
}

async function withAuthMutationLock<T>(operation: () => Promise<T>): Promise<T> {
  if (typeof navigator !== 'undefined' && navigator.locks) {
    return navigator.locks.request(AUTH_MUTATION_LOCK, operation);
  }

  // Web Locks 미지원 환경에서도 같은 탭 안의 로그인/갱신/로그아웃은 직렬화한다.
  const previous = authMutationTail;
  let release!: () => void;
  authMutationTail = new Promise<void>((resolve) => {
    release = resolve;
  });
  await previous.catch(() => undefined);
  try {
    return await operation();
  } finally {
    release();
  }
}

async function refreshAuthSessionUnlocked(expected: AuthSession): Promise<AuthSession | null> {
  const beforeRefresh = getAuthSession();
  if (!sameRefreshIdentity(beforeRefresh, expected)) {
    return beforeRefresh?.user.id === expected.user.id ? beforeRefresh : null;
  }

  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Auth-Transport': 'cookie',
      },
      credentials: 'include',
      body: JSON.stringify(
        expected.session.refresh_token
          ? { refresh_token: expected.session.refresh_token }
          : {},
      ),
    });
    const body = await response.json().catch(() => ({}));
    if (
      !response.ok
      || !body.session
      || !body.user?.id
      || body.user.id !== expected.user.id
    ) {
      if (sameRefreshIdentity(getAuthSession(), expected)) {
        setAuthSession(null);
      }
      return null;
    }
    const next = withoutRefreshToken({
      user: {
        id: body.user.id,
        email: body.user.email ?? expected.user.email,
      },
      session: body.session,
    });
    if (sameRefreshIdentity(getAuthSession(), expected)) {
      setAuthSession(next);
      return next;
    }
    const latest = getAuthSession();
    return latest?.user.id === expected.user.id ? latest : null;
  } catch {
    return null;
  }
}

function withBearer(
  init: RequestInit | undefined,
  token: string | undefined,
  replace = false,
): RequestInit {
  const headers = new Headers(init?.headers);
  if (token && (replace || !headers.has('Authorization'))) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return { ...init, headers };
}

async function isRefreshableAuthFailure(response: Response): Promise<boolean> {
  if (response.status !== 401) return false;
  const challenge = response.headers.get('WWW-Authenticate')?.toLowerCase() ?? '';
  if (challenge.includes('invalid_token')) return true;
  const body = await response.clone().json().catch(() => ({}));
  return body.code === 'TOKEN_EXPIRED' || body.code === 'TOKEN_INVALID';
}

export async function authFetch(input: string | URL, init?: RequestInit): Promise<Response> {
  const current = getAuthSession();
  const suppliedAuthorization = new Headers(init?.headers).get('Authorization');
  const usesManagedAuthorization = !suppliedAuthorization
    || suppliedAuthorization === `Bearer ${current?.session.access_token}`;
  let response = await fetch(input, withBearer(init, current?.session.access_token));
  if (
    !current
    || !usesManagedAuthorization
    || !(await isRefreshableAuthFailure(response))
  ) {
    return response;
  }

  return withAuthMutationLock(async () => {
    const latest = getAuthSession();
    if (!latest || latest.user.id !== current.user.id) return response;

    // 다른 401 요청이 먼저 갱신했다면 그 세션을 재사용하고, 아니면 이 요청이
    // 쿠키를 회전한다. 보호 요청 재시도까지 잠금을 유지해 계정 전환과 겹치지 않는다.
    const refreshed = sameRefreshIdentity(latest, current)
      ? await refreshAuthSessionUnlocked(current)
      : latest;
    if (!refreshed || refreshed.user.id !== current.user.id) return response;

    response = await fetch(
      input,
      withBearer(init, refreshed.session.access_token, true),
    );
    if (
      await isRefreshableAuthFailure(response)
      && sameRefreshIdentity(getAuthSession(), refreshed)
    ) {
      setAuthSession(null);
    }
    return response;
  });
}

export async function signOut(): Promise<void> {
  return withAuthMutationLock(async () => {
    const signingOut = getAuthSession();
    try {
      let active = signingOut;
      let response = await fetch(
        `${API_BASE}/api/auth/logout`,
        withBearer({ method: 'POST', credentials: 'include' }, active?.session.access_token),
      );
      if (active && await isRefreshableAuthFailure(response)) {
        active = await refreshAuthSessionUnlocked(active);
        if (active) {
          response = await fetch(
            `${API_BASE}/api/auth/logout`,
            withBearer(
              { method: 'POST', credentials: 'include' },
              active.session.access_token,
              true,
            ),
          );
        }
      }
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${response.status}`);
      }
    } finally {
      const latest = getAuthSession();
      if (!signingOut || !latest || latest.user.id === signingOut.user.id) {
        setAuthSession(null);
      }
    }
  });
}

export const AUTH_SESSION_STORAGE_KEY = AUTH_STORAGE_KEY;

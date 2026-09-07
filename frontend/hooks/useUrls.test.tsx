import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import { useAuthUserId } from '@/hooks/useAuthUserId';
import { useUrls } from './useUrls';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

type UrlHook = ReturnType<typeof useUrls>;

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

let currentHook: UrlHook | null = null;
const observations: Array<{ userId: string | null; urls: string[] }> = [];

function Harness() {
  const userId = useAuthUserId();
  const hook = useUrls();
  useEffect(() => {
    currentHook = hook;
    observations.push({ userId, urls: [...hook.urls] });
  }, [hook, userId]);
  return null;
}

describe('useUrls 계정 격리', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    setAuthSession(null);
    localStorage.clear();
    currentHook = null;
    observations.length = 0;
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    setAuthSession(null);
    container.remove();
    currentHook = null;
  });

  it('A URL 큐를 B에 노출하지 않고 다시 A로 돌아와도 임시 큐를 복원하지 않는다', async () => {
    setAuthSession(authSession('account-a'));
    await act(async () => root.render(<Harness />));
    await act(async () => {
      currentHook!.addUrl('https://a.example/video');
    });
    expect(currentHook?.urls).toEqual(['https://a.example/video']);

    const observationStart = observations.length;
    await act(async () => setAuthSession(authSession('account-b')));
    expect(currentHook?.urls).toEqual([]);
    expect(
      observations.slice(observationStart).some(
        ({ userId, urls }) => userId === 'account-b' && urls.includes('https://a.example/video'),
      ),
    ).toBe(false);

    await act(async () => {
      currentHook!.addUrl('https://b.example/video');
    });
    expect(currentHook?.urls).toEqual(['https://b.example/video']);

    await act(async () => setAuthSession(authSession('account-a')));
    expect(currentHook?.urls).toEqual([]);
  });

  it('A 렌더에서 캡처한 오래된 제거 콜백이 B URL 큐를 변경하지 못한다', async () => {
    setAuthSession(authSession('account-a'));
    await act(async () => root.render(<Harness />));
    await act(async () => {
      currentHook!.addUrl('https://a.example/video');
    });
    const staleRemoveUrl = currentHook!.removeUrl;

    await act(async () => setAuthSession(authSession('account-b')));
    await act(async () => {
      currentHook!.addUrl('https://b.example/video');
    });
    expect(currentHook?.urls).toEqual(['https://b.example/video']);

    await act(async () => {
      staleRemoveUrl('https://a.example/video');
    });
    expect(currentHook?.urls).toEqual(['https://b.example/video']);
  });
});

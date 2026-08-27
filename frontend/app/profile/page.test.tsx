import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import { getAccountStorageKey, getStorageAccountNamespace } from '@/lib/storage';
import ProfilePage, { PROFILE_STORAGE_KEY } from './page';

vi.mock('next/link', () => ({
  default: ({ children, href }: React.PropsWithChildren<{ href: string }>) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function storedProfile(displayName: string) {
  return JSON.stringify({
    displayName,
    email: `${displayName.toLowerCase()}@example.com`,
    plan: 'Free',
    usageUsed: 1,
    usageTotal: 30,
    memberSince: '2026-01-01',
  });
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function flushRender() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe('ProfilePage account isolation', () => {
  beforeEach(() => {
    setAuthSession(null);
    localStorage.clear();
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    setAuthSession(null);
    localStorage.clear();
    document.body.innerHTML = '';
    root = null;
    container = null;
  });

  it('A → 로그아웃 → B 전환 시 프로필을 즉시 교체하고 각 키를 보존한다', async () => {
    const keyA = getAccountStorageKey(
      PROFILE_STORAGE_KEY,
      getStorageAccountNamespace('account-a'),
    );
    const keyB = getAccountStorageKey(
      PROFILE_STORAGE_KEY,
      getStorageAccountNamespace('account-b'),
    );
    localStorage.setItem(keyA, storedProfile('Alice'));
    localStorage.setItem(keyB, storedProfile('Bob'));
    setAuthSession(authSession('account-a'));

    await act(async () => root!.render(<ProfilePage />));
    await flushRender();
    expect(container?.textContent).toContain('Alice');
    expect(container?.textContent).not.toContain('Bob');

    await act(async () => setAuthSession(null));
    await flushRender();
    expect(container?.textContent).not.toContain('Alice');
    expect(container?.textContent).not.toContain('Bob');

    await act(async () => setAuthSession(authSession('account-b')));
    await flushRender();
    expect(container?.textContent).toContain('Bob');
    expect(container?.textContent).not.toContain('Alice');
    expect(localStorage.getItem(keyA)).toContain('Alice');
    expect(localStorage.getItem(keyB)).toContain('Bob');
  });
});

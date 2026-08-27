'use client';

import { useSyncExternalStore } from 'react';
import { getAuthSession, subscribeAuthSession } from '@/lib/auth-session';

const subscribers = new Set<() => void>();
let unsubscribeAuthSession: (() => void) | null = null;

function subscribeAuthUserId(listener: () => void): () => void {
  subscribers.add(listener);
  if (!unsubscribeAuthSession) {
    unsubscribeAuthSession = subscribeAuthSession(() => {
      [...subscribers].forEach((subscriber) => subscriber());
    });
  }
  return () => {
    subscribers.delete(listener);
    if (subscribers.size === 0) {
      unsubscribeAuthSession?.();
      unsubscribeAuthSession = null;
    }
  };
}

function getAuthUserIdSnapshot(): string | null {
  return getAuthSession()?.user.id ?? null;
}

function getServerAuthUserIdSnapshot(): null {
  return null;
}

/** 현재 인증 사용자 ID를 같은 탭·다른 탭 전환까지 포함해 구독합니다. */
export function useAuthUserId(): string | null {
  return useSyncExternalStore(
    subscribeAuthUserId,
    getAuthUserIdSnapshot,
    getServerAuthUserIdSnapshot,
  );
}

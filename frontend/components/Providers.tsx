'use client';

import {
  CancelledError,
  QueryClient,
  QueryClientProvider,
  type QueryClient as QueryClientType,
} from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import {
  useCallback,
  useRef,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from 'react';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { getAuthSession, subscribeAuthSession } from '@/lib/auth-session';
import { I18nProvider } from '@/lib/i18n/I18nProvider';

export const ANONYMOUS_AUTH_SCOPE = 'anonymous';
export type AuthScope = typeof ANONYMOUS_AUTH_SCOPE | `user:${string}`;

const protectedMutationControllers = new Map<AbortController, AuthScope>();

export function getAuthScopeSnapshot(): AuthScope {
  const userId = getAuthSession()?.user.id;
  return userId ? `user:${userId}` : ANONYMOUS_AUTH_SCOPE;
}

function getServerAuthScopeSnapshot(): AuthScope {
  return ANONYMOUS_AUTH_SCOPE;
}

export function useAuthScope(): AuthScope {
  return useSyncExternalStore(
    subscribeAuthSession,
    getAuthScopeSnapshot,
    getServerAuthScopeSnapshot,
  );
}

export function isCurrentAuthScope(authScope: AuthScope): boolean {
  return getAuthScopeSnapshot() === authScope;
}

export function protectedAuthMeta(authScope: AuthScope) {
  return { authProtected: true, authScope } as const;
}

/**
 * React Query v5 does not expose cancelMutations. This cancellation boundary
 * settles the mutation as cancelled immediately while the underlying API call
 * is allowed to finish without reaching a stale success callback.
 */
export async function runProtectedMutation<T>(
  authScope: AuthScope,
  operation: () => Promise<T>,
): Promise<T> {
  if (!isCurrentAuthScope(authScope)) {
    throw new CancelledError({ silent: true });
  }

  const controller = new AbortController();
  protectedMutationControllers.set(controller, authScope);

  let cancel: (() => void) | undefined;
  const cancelled = new Promise<never>((_resolve, reject) => {
    cancel = () => reject(new CancelledError({ silent: true }));
    controller.signal.addEventListener('abort', cancel, { once: true });
  });
  let running: Promise<T>;
  try {
    // Start while the scope check above still matches, so authFetch snapshots
    // the initiating account before a later session-change event can run.
    running = operation();
  } catch (error) {
    running = Promise.reject(error);
  }

  try {
    return await Promise.race([running, cancelled]);
  } finally {
    if (cancel) controller.signal.removeEventListener('abort', cancel);
    protectedMutationControllers.delete(controller);
  }
}

function purgeProtectedAuthState(
  queryClient: QueryClientType,
  authScope: AuthScope,
): void {
  const protectedQueryFilter = {
    predicate: (query: { meta?: Record<string, unknown> }) =>
      query.meta?.authProtected === true
      && query.meta.authScope === authScope,
  };

  for (const [controller, controllerAuthScope] of protectedMutationControllers) {
    if (controllerAuthScope === authScope) controller.abort();
  }

  void queryClient.cancelQueries(protectedQueryFilter, { silent: true });
  queryClient.removeQueries(protectedQueryFilter);

  const mutationCache = queryClient.getMutationCache();
  for (const mutation of mutationCache.getAll()) {
    if (
      mutation.meta?.authProtected === true
      && mutation.meta.authScope === authScope
    ) {
      mutationCache.remove(mutation);
    }
  }
}

function useAuthQueryBoundary(queryClient: QueryClientType): void {
  const previousAuthScope = useRef(getAuthScopeSnapshot());
  const subscribe = useCallback(
    (onStoreChange: () => void) =>
      subscribeAuthSession(() => {
        const nextAuthScope = getAuthScopeSnapshot();
        if (nextAuthScope !== previousAuthScope.current) {
          purgeProtectedAuthState(queryClient, previousAuthScope.current);
          previousAuthScope.current = nextAuthScope;
        }
        onStoreChange();
      }),
    [queryClient],
  );

  useSyncExternalStore(
    subscribe,
    getAuthScopeSnapshot,
    getServerAuthScopeSnapshot,
  );
}

export default function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 30_000 },
        },
      })
  );

  useAuthQueryBoundary(queryClient);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <I18nProvider>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider delayDuration={300}>
            {children}
            <Toaster position="bottom-right" richColors />
          </TooltipProvider>
        </QueryClientProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}

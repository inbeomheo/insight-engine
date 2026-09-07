import { act, useEffect, type PropsWithChildren } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Providers from '@/components/Providers';
import {
  AUTH_SESSION_STORAGE_KEY,
  setAuthSession,
  type AuthSession,
} from '@/lib/auth-session';
import { useKnowledge } from './useKnowledge';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  getKnowledgeList: vi.fn(),
  uploadKnowledge: vi.fn(),
  deleteKnowledge: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  getKnowledgeList: mocks.getKnowledgeList,
  uploadKnowledge: mocks.uploadKnowledge,
  deleteKnowledge: mocks.deleteKnowledge,
}));
vi.mock('sonner', () => ({
  toast: { success: mocks.toastSuccess, error: mocks.toastError },
}));
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

let latestKnowledge: ReturnType<typeof useKnowledge> | null = null;
let observedClient: QueryClient | null = null;

function Harness({
  onChange,
}: {
  onChange: (
    knowledge: ReturnType<typeof useKnowledge>,
    queryClient: QueryClient,
  ) => void;
}) {
  const knowledge = useKnowledge();
  const queryClient = useQueryClient();

  useEffect(() => onChange(knowledge, queryClient), [knowledge, onChange, queryClient]);

  return <output>{knowledge.documents.map((document) => document.filename).join(',')}</output>;
}

function captureKnowledge(
  knowledge: ReturnType<typeof useKnowledge>,
  queryClient: QueryClient,
) {
  latestKnowledge = knowledge;
  observedClient = queryClient;
}

describe('useKnowledge 계정 격리', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    latestKnowledge = null;
    observedClient = null;
    for (const mock of [
      mocks.getKnowledgeList,
      mocks.uploadKnowledge,
      mocks.deleteKnowledge,
      mocks.toastSuccess,
      mocks.toastError,
    ]) {
      mock.mockReset();
    }
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
  });

  it('A 문서와 느지막한 upload 콜백을 B 범위에 적용하지 않는다', async () => {
    const listA = deferred<{
      documents: Array<{
        id: string;
        filename: string;
        uploaded_at: string;
        chunk_count: number;
      }>;
    }>();
    const listB = deferred<{
      documents: Array<{
        id: string;
        filename: string;
        uploaded_at: string;
        chunk_count: number;
      }>;
    }>();
    const uploadA = deferred<{
      id: string;
      filename: string;
      uploaded_at: string;
      chunk_count: number;
    }>();
    mocks.getKnowledgeList
      .mockReturnValueOnce(listA.promise)
      .mockReturnValueOnce(listB.promise);
    mocks.uploadKnowledge.mockReturnValueOnce(uploadA.promise);
    setAuthSession(AUTH_A);

    await act(async () => {
      root.render(
        <Providers>
          <Harness onChange={captureKnowledge} />
        </Providers>,
      );
    });
    await vi.waitFor(() => expect(mocks.getKnowledgeList).toHaveBeenCalledTimes(1));

    listA.resolve({
      documents: [{
        id: 'doc-a',
        filename: 'account-a.md',
        uploaded_at: '2026-08-27T00:00:00Z',
        chunk_count: 1,
      }],
    });
    await vi.waitFor(() => expect(container.textContent).toBe('account-a.md'));

    await act(async () => {
      latestKnowledge!.upload(new File(['A'], 'late-a.md'));
    });
    await vi.waitFor(() => expect(mocks.uploadKnowledge).toHaveBeenCalledTimes(1));

    await act(async () => {
      setAuthSession(AUTH_B);
    });

    expect(latestKnowledge!.documents).toEqual([]);
    expect(latestKnowledge!.isUploading).toBe(false);
    expect(observedClient!.getQueryData([
      'protected',
      'user:account-a',
      'knowledge',
    ])).toBeUndefined();
    await vi.waitFor(() => expect(mocks.getKnowledgeList).toHaveBeenCalledTimes(2));

    listB.resolve({
      documents: [{
        id: 'doc-b',
        filename: 'account-b.md',
        uploaded_at: '2026-08-27T00:00:00Z',
        chunk_count: 2,
      }],
    });
    await vi.waitFor(() => expect(container.textContent).toBe('account-b.md'));

    uploadA.resolve({
      id: 'late-a',
      filename: 'late-a.md',
      uploaded_at: '2026-08-27T00:00:00Z',
      chunk_count: 3,
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(container.textContent).toBe('account-b.md');
    expect(mocks.getKnowledgeList).toHaveBeenCalledTimes(2);
    expect(mocks.toastSuccess).not.toHaveBeenCalled();
    expect(mocks.toastError).not.toHaveBeenCalled();
    expect(observedClient!.getQueryData([
      'protected',
      'user:account-b',
      'knowledge',
    ])).toEqual({
      documents: [expect.objectContaining({ id: 'doc-b' })],
    });
  });
});

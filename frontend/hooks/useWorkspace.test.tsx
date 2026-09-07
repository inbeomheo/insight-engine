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
import type { Workspace } from '@/lib/types';
import { useWorkspace } from './useWorkspace';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  getWorkspaces: vi.fn(),
  createWorkspace: vi.fn(),
  getWorkspaceMembers: vi.fn(),
  inviteMember: vi.fn(),
  removeMember: vi.fn(),
  deleteWorkspace: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  getWorkspaces: mocks.getWorkspaces,
  createWorkspace: mocks.createWorkspace,
  getWorkspaceMembers: mocks.getWorkspaceMembers,
  inviteMember: mocks.inviteMember,
  removeMember: mocks.removeMember,
  deleteWorkspace: mocks.deleteWorkspace,
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

const WORKSPACE_A: Workspace = {
  id: 'workspace-a',
  name: 'A workspace',
  owner_id: 'account-a',
  created_at: '2026-08-27T00:00:00Z',
};
const WORKSPACE_B: Workspace = {
  id: 'workspace-b',
  name: 'B workspace',
  owner_id: 'account-b',
  created_at: '2026-08-27T00:00:00Z',
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

let latestWorkspace: ReturnType<typeof useWorkspace> | null = null;
let observedClient: QueryClient | null = null;

function Harness({
  onChange,
}: {
  onChange: (
    workspace: ReturnType<typeof useWorkspace>,
    queryClient: QueryClient,
  ) => void;
}) {
  const workspace = useWorkspace(true);
  const queryClient = useQueryClient();

  useEffect(() => onChange(workspace, queryClient), [onChange, queryClient, workspace]);

  return (
    <output>
      {workspace.activeWorkspaceId ?? 'none'}|
      {workspace.workspaces.map((item) => item.name).join(',')}
    </output>
  );
}

function captureWorkspace(
  workspace: ReturnType<typeof useWorkspace>,
  queryClient: QueryClient,
) {
  latestWorkspace = workspace;
  observedClient = queryClient;
}

describe('useWorkspace 계정 격리', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    latestWorkspace = null;
    observedClient = null;
    for (const mock of Object.values(mocks)) mock.mockReset();
    mocks.getWorkspaceMembers.mockResolvedValue({ members: [] });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
    localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
  });

  it('계정 전환 시 활성 workspace를 즉시 초기화하고 A의 느지막한 생성 결과를 무시한다', async () => {
    const listA = deferred<{ workspaces: Workspace[] }>();
    const listB = deferred<{ workspaces: Workspace[] }>();
    const createA = deferred<Workspace>();
    mocks.getWorkspaces
      .mockReturnValueOnce(listA.promise)
      .mockReturnValueOnce(listB.promise);
    mocks.createWorkspace.mockReturnValueOnce(createA.promise);
    setAuthSession(AUTH_A);

    await act(async () => {
      root.render(
        <Providers>
          <Harness onChange={captureWorkspace} />
        </Providers>,
      );
    });
    await vi.waitFor(() => expect(mocks.getWorkspaces).toHaveBeenCalledTimes(1));

    listA.resolve({ workspaces: [WORKSPACE_A] });
    await vi.waitFor(() => expect(container.textContent).toContain('A workspace'));

    await act(async () => {
      latestWorkspace!.switchWorkspace(WORKSPACE_A.id);
    });
    expect(latestWorkspace!.activeWorkspaceId).toBe(WORKSPACE_A.id);

    await act(async () => {
      latestWorkspace!.create('late A workspace');
    });
    await vi.waitFor(() => expect(mocks.createWorkspace).toHaveBeenCalledTimes(1));

    await act(async () => {
      setAuthSession(AUTH_B);
    });

    expect(latestWorkspace!.activeWorkspaceId).toBeNull();
    expect(latestWorkspace!.workspaces).toEqual([]);
    expect(observedClient!.getQueryData([
      'protected',
      'user:account-a',
      'workspaces',
    ])).toBeUndefined();
    await vi.waitFor(() => expect(mocks.getWorkspaces).toHaveBeenCalledTimes(2));

    listB.resolve({ workspaces: [WORKSPACE_B] });
    await vi.waitFor(() => expect(container.textContent).toBe('none|B workspace'));

    createA.resolve({
      ...WORKSPACE_A,
      id: 'late-workspace-a',
      name: 'late A workspace',
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(latestWorkspace!.activeWorkspaceId).toBeNull();
    expect(container.textContent).toBe('none|B workspace');
    expect(mocks.getWorkspaces).toHaveBeenCalledTimes(2);
    expect(mocks.toastSuccess).not.toHaveBeenCalled();
    expect(mocks.toastError).not.toHaveBeenCalled();
    expect(observedClient!.getQueryData([
      'protected',
      'user:account-b',
      'workspaces',
    ])).toEqual([WORKSPACE_B]);
  });
});

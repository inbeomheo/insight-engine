import { act, type ReactNode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAuthSession } from '@/lib/auth-session';
import type { NoteGraphResponse } from '@/lib/note-graph';
import NoteGraphPage from './page';
import NotesLayout from '../layout';

const navigation = vi.hoisted(() => ({ pathname: '/notes/graph' }));
vi.mock('next/navigation', () => ({ usePathname: () => navigation.pathname }));
vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

function login(userId: string | null) {
  setAuthSession(userId ? { user: { id: userId }, session: { access_token: `${userId}-token` } } : null);
}

function graph(title: string): NoteGraphResponse {
  return {
    nodes: [{ id: title, title, key_concepts: [], created_at: '' }],
    edges: [],
    meta: { node_limit: 24, edge_limit: 80, related_limit: 3, min_score: 0.2, node_count: 1, edge_count: 0 },
  };
}

function json(value: unknown) {
  return new Response(JSON.stringify(value), { status: 200 });
}

function deferred() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((done) => { resolve = done; });
  return { promise, resolve };
}

let root: Root;
let container: HTMLDivElement;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  navigation.pathname = '/notes/graph';
  login('user-a');
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  login(null);
  vi.unstubAllGlobals();
});

async function render(content: ReactNode) {
  await act(async () => root.render(content));
}

describe('노트 관계 화면의 계정 전환', () => {
  it('그래프에서 이전 계정 자료를 즉시 지우고 새 계정 토큰으로 다시 요청한다', async () => {
    const pendingB = deferred();
    const fetchMock = vi.fn().mockResolvedValueOnce(json(graph('A 비공개 그래프'))).mockReturnValueOnce(pendingB.promise);
    vi.stubGlobal('fetch', fetchMock);
    await render(<NoteGraphPage />);
    expect(container.textContent).toContain('A 비공개 그래프');

    await act(async () => login('user-b'));
    expect(container.textContent).not.toContain('A 비공개 그래프');
    expect(fetchMock.mock.calls[1][1].headers.get('Authorization')).toBe('Bearer user-b-token');
    await act(async () => pendingB.resolve(json(graph('B 그래프'))));
    expect(container.textContent).toContain('B 그래프');
  });

  it('이전 계정의 늦은 그래프 응답이 새 계정 화면을 덮어쓰지 않는다', async () => {
    const pendingA = deferred();
    vi.stubGlobal('fetch', vi.fn().mockReturnValueOnce(pendingA.promise).mockResolvedValueOnce(json(graph('B 그래프'))));
    await render(<NoteGraphPage />);
    await act(async () => login('user-b'));
    await act(async () => pendingA.resolve(json(graph('A 비공개 그래프'))));
    expect(container.textContent).toContain('B 그래프');
    expect(container.textContent).not.toContain('A 비공개 그래프');
  });

  it('상세 레이아웃에 역방향 패널이 한 번 표시되고 계정 전환 시 이전 연결을 지운다', async () => {
    navigation.pathname = '/notes/target';
    const pendingB = deferred();
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ notes: [{ id: 'a', title: 'A 비공개 연결', score: 0.9 }] })).mockReturnValueOnce(pendingB.promise);
    vi.stubGlobal('fetch', fetchMock);
    await render(<NotesLayout><p>노트 상세</p></NotesLayout>);
    expect(container.querySelectorAll('#note-backlinks-title')).toHaveLength(1);
    expect(container.textContent).toContain('A 비공개 연결');
    expect(fetchMock.mock.calls[0][0]).toBe('/api/notes/target/backlinks');

    await act(async () => login('user-b'));
    expect(container.textContent).not.toContain('A 비공개 연결');
    expect(fetchMock.mock.calls[1][1].headers.get('Authorization')).toBe('Bearer user-b-token');
    await act(async () => pendingB.resolve(json({ notes: [{ id: 'b', title: 'B 연결', score: 0.8 }] })));
    expect(container.textContent).toContain('B 연결');
  });

  it('로그아웃 후 늦게 도착한 역방향 응답을 버린다', async () => {
    navigation.pathname = '/notes/target';
    const pendingA = deferred();
    vi.stubGlobal('fetch', vi.fn().mockReturnValueOnce(pendingA.promise).mockResolvedValueOnce(new Response('{}', { status: 401 })));
    await render(<NotesLayout><p>노트 상세</p></NotesLayout>);
    await act(async () => login(null));
    await act(async () => pendingA.resolve(json({ notes: [{ id: 'a', title: 'A 비공개 연결', score: 0.9 }] })));
    expect(container.textContent).not.toContain('A 비공개 연결');
    expect(container.textContent).toContain('로그인이 필요합니다.');
  });
});

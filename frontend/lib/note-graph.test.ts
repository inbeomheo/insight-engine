import { afterEach, describe, expect, it, vi } from 'vitest';
import { setAuthSession } from './auth-session';

import {
  buildCircularGraphLayout,
  connectedNodeIds,
  getNoteBacklinks,
  getNoteGraph,
  type NoteGraphNode,
} from './note-graph';

const node = (id: string): NoteGraphNode => ({
  id,
  title: `note-${id}`,
  key_concepts: [],
  created_at: '',
});

afterEach(() => {
  setAuthSession(null);
  vi.unstubAllGlobals();
});

describe('노트 관계 인증 요청', () => {
  it('그래프와 역방향 요청에 현재 사용자 인증 토큰을 전달한다', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    setAuthSession({ user: { id: 'user-a' }, session: { access_token: 'token-a' } });
    await getNoteGraph();
    setAuthSession({ user: { id: 'user-b' }, session: { access_token: 'token-b' } });
    await getNoteBacklinks('note/id');

    expect(fetchMock.mock.calls[0][0]).toBe('/api/notes/graph');
    expect(fetchMock.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer token-a');
    expect(fetchMock.mock.calls[1][0]).toBe('/api/notes/note%2Fid/backlinks');
    expect(fetchMock.mock.calls[1][1].headers.get('Authorization')).toBe('Bearer token-b');
  });

  it.each([401, 403])('인증 거절 %i를 화면용 오류로 전달한다', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status })));
    await expect(getNoteGraph()).rejects.toThrow('로그인이 필요합니다.');
  });
});

describe('note graph helpers', () => {
  it('places one node at the center and many nodes deterministically', () => {
    expect(buildCircularGraphLayout([node('a')])).toEqual([
      { ...node('a'), x: 50, y: 50 },
    ]);

    const first = buildCircularGraphLayout([node('a'), node('b'), node('c')]);
    const second = buildCircularGraphLayout([node('a'), node('b'), node('c')]);
    expect(second).toEqual(first);
    expect(first.every((point) => point.x >= 0 && point.x <= 100)).toBe(true);
    expect(first.every((point) => point.y >= 0 && point.y <= 100)).toBe(true);
  });

  it('collects both incoming and outgoing neighbours for focus highlighting', () => {
    const ids = connectedNodeIds('b', [
      { source: 'a', target: 'b', score: 0.8 },
      { source: 'b', target: 'c', score: 0.7 },
      { source: 'x', target: 'y', score: 0.9 },
    ]);

    expect([...ids].sort()).toEqual(['a', 'b', 'c']);
  });
});

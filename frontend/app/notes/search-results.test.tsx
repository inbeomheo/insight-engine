import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { NoteListItem, NoteSearchResult } from '@/lib/api';
import { SearchResultsList } from './page';

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn() }),
}));

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function renderSearchResults(results: NoteSearchResult[], notes: NoteListItem[]) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(<SearchResultsList results={results} notes={notes} />);
  });
  return container;
}

function result(id = 'note/id'): NoteSearchResult {
  return {
    id,
    title: '검색 노트',
    score: 0.91,
    snippet: '검색 근거 요약',
  };
}

function note(id = 'note/id'): NoteListItem {
  return {
    id,
    title: '검색 노트',
    tags: [],
    key_concepts: ['RAG', '벡터'],
    quote_count: 2,
    learning_point_count: 1,
    review_question_count: 2,
    created_at: '2026-07-12T00:00:00.000Z',
    source: { type: 'text', url: '', title: '검색 노트' },
  };
}

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
});

afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  container?.remove();
  root = null;
  container = null;
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('SearchResultsList', () => {
  it('renders separate accessible document, quote, study, and chat links without nesting', async () => {
    const view = await renderSearchResults([result()], [note()]);
    const nav = view.querySelector('nav[aria-label="검색 노트 바로가기"]');

    expect(nav).not.toBeNull();
    expect(Array.from(nav!.querySelectorAll('a')).map((link) => link.getAttribute('href'))).toEqual([
      '/notes/note%2Fid',
      '/notes/note%2Fid#quotes',
      '/notes/note%2Fid#study-progress',
      '/notes/note%2Fid#chat',
    ]);
    expect(view.querySelector('a a')).toBeNull();
    expect(Array.from(nav!.querySelectorAll('a')).map((link) => link.getAttribute('aria-label'))).toEqual([
      '검색 노트 문서 열기',
      '검색 노트 근거 보기',
      '검색 노트 복습 시작',
      '검색 노트 근거 Q&A',
    ]);
    expect(view.textContent).toContain('RAG');
    expect(view.textContent).toContain('인용 2');
    expect(view.textContent).toContain('학습·복습 3');
  });

  it('keeps unmatched results usable without metadata-only actions', async () => {
    const view = await renderSearchResults([result('missing note')], []);
    const nav = view.querySelector('nav[aria-label="검색 노트 바로가기"]');

    expect(Array.from(nav!.querySelectorAll('a')).map((link) => link.getAttribute('href'))).toEqual([
      '/notes/missing%20note',
      '/notes/missing%20note#chat',
    ]);
    expect(view.querySelector('[aria-label="검색 노트 근거 보기"]')).toBeNull();
    expect(view.querySelector('[aria-label="검색 노트 복습 시작"]')).toBeNull();
    expect(view.querySelector('a a')).toBeNull();
  });
});

import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { NoteListItem, NoteSearchResult } from '@/lib/api';
import { SearchResultsList, shouldHandleFacetLinkClick } from './page';

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

async function renderSearchResults(
  results: NoteSearchResult[],
  notes: NoteListItem[],
  onFacetSelect = vi.fn()
) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <SearchResultsList
        results={results}
        notes={notes}
        onFacetSelect={onFacetSelect}
      />
    );
  });
  return container;
}

function result(id = 'note/id'): NoteSearchResult {
  return {
    id,
    title: '검색 노트',
    score: 0.91,
    snippet: '검색 근거 요약',
    highlight_ranges: [[3, 8]],
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

  it('links key concepts to encoded wiki facets and intercepts only plain activation', async () => {
    const onFacetSelect = vi.fn();
    const view = await renderSearchResults([result()], [note()], onFacetSelect);
    const ragLink = view.querySelector<HTMLAnchorElement>('[aria-label="RAG 개념으로 탐색"]');
    const vectorLink = view.querySelector<HTMLAnchorElement>('[aria-label="벡터 개념으로 탐색"]');

    expect(ragLink?.getAttribute('href')).toBe('/notes?concept=RAG');
    expect(vectorLink?.getAttribute('href')).toBe('/notes?concept=%EB%B2%A1%ED%84%B0');

    const plainClick = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 });
    await act(async () => { ragLink!.dispatchEvent(plainClick); });
    expect(plainClick.defaultPrevented).toBe(true);
    expect(onFacetSelect).toHaveBeenCalledWith({ type: 'concept', value: 'RAG' });

    const modifiedClicks = [
      { ctrlKey: true },
      { metaKey: true },
      { shiftKey: true },
      { altKey: true },
      { button: 1 },
    ];
    const stopTestNavigation = (event: MouseEvent) => event.preventDefault();
    document.addEventListener('click', stopTestNavigation);
    try {
      for (const init of modifiedClicks) {
        const event = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0, ...init });
        expect(shouldHandleFacetLinkClick(event)).toBe(false);
        await act(async () => { ragLink!.dispatchEvent(event); });
      }
    } finally {
      document.removeEventListener('click', stopTestNavigation);
    }
    expect(onFacetSelect).toHaveBeenCalledTimes(1);
    expect(shouldHandleFacetLinkClick({ button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false })).toBe(true);
    expect(view.querySelector('a a')).toBeNull();
  });

  it('marks only the matched snippet phrase and preserves the full snippet text', async () => {
    const view = await renderSearchResults([result()], [note()]);
    const snippet = view.querySelector('p.line-clamp-2');
    const mark = snippet?.querySelector('mark');

    expect(snippet?.textContent).toBe('검색 근거 요약');
    expect(mark?.textContent).toBe('근거 요약');
    expect(mark?.className).toContain('bg-primary/15');
    expect(view.querySelector('a mark')).toBeNull();
    expect(view.querySelector('a a')).toBeNull();
  });

  it('renders the original snippet without mark when the server returns no highlight range', async () => {
    const withoutHighlight = { ...result(), highlight_ranges: [] };
    const view = await renderSearchResults([withoutHighlight], [note()]);
    const snippet = view.querySelector('p.line-clamp-2');

    expect(snippet?.textContent).toBe('검색 근거 요약');
    expect(snippet?.querySelector('mark')).toBeNull();
  });
});

import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getNotes,
  searchNotes,
  type NoteListItem,
  type NoteSearchResult,
} from '@/lib/api';
import NotesPage, { ActiveFacetBar, SearchResultsList, shouldHandleFacetLinkClick } from './page';

vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

const replaceMock = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    getNotes: vi.fn(),
    searchNotes: vi.fn(),
  };
});

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

async function renderNotesPage() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(<NotesPage />);
  });
  return container;
}

async function renderActiveFacetBar({
  searchReturnQuery,
  onReturnToSearch = vi.fn(),
  onClear = vi.fn(),
}: {
  searchReturnQuery: string | null;
  onReturnToSearch?: () => void;
  onClear?: () => void;
}) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <ActiveFacetBar
        facet={{ type: 'concept', value: 'RAG' }}
        resultCount={1}
        totalCount={4}
        searchReturnQuery={searchReturnQuery}
        searchReturnCount={2}
        onReturnToSearch={onReturnToSearch}
        onClear={onClear}
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
  window.history.replaceState({}, '', '/notes');
  window.localStorage.clear();
  replaceMock.mockReset();
  vi.mocked(getNotes).mockReset();
  vi.mocked(searchNotes).mockReset();
  vi.mocked(getNotes).mockResolvedValue({ notes: [note()] });
  vi.mocked(searchNotes).mockResolvedValue({ notes: [result()] });
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

describe('ActiveFacetBar', () => {
  it('returns to the preserved search session while keeping the clear action', async () => {
    const onReturnToSearch = vi.fn();
    const onClear = vi.fn();
    const view = await renderActiveFacetBar({
      searchReturnQuery: 'RAG 검색',
      onReturnToSearch,
      onClear,
    });
    const buttons = Array.from(view.querySelectorAll('button'));
    const returnButton = buttons.find((button) => button.textContent?.includes('검색 결과로 돌아가기'));
    const clearButton = buttons.find((button) => button.textContent?.includes('필터 해제'));

    expect(view.textContent).toContain('개념: RAG');
    expect(view.textContent).toContain('1/4개 노트');
    expect(returnButton?.textContent).toContain('(2)');

    await act(async () => { returnButton?.click(); });
    await act(async () => { clearButton?.click(); });
    expect(onReturnToSearch).toHaveBeenCalledOnce();
    expect(onClear).toHaveBeenCalledOnce();
  });

  it('hides the return action without a preserved search session', async () => {
    const view = await renderActiveFacetBar({ searchReturnQuery: null });

    expect(view.textContent).not.toContain('검색 결과로 돌아가기');
    expect(view.textContent).toContain('필터 해제');
  });
});

describe('NotesPage search return flow', () => {
  it('restores the submitted query, result snippet, highlight, and clean route after a concept pivot', async () => {
    const view = await renderNotesPage();
    const input = view.querySelector<HTMLInputElement>('input[placeholder^="노트 검색"]');
    const form = input?.closest('form');

    expect(input).not.toBeNull();
    expect(form).not.toBeNull();

    await act(async () => {
      const setValue = Object.getOwnPropertyDescriptor(
        HTMLInputElement.prototype,
        'value',
      )?.set;
      setValue?.call(input, 'RAG 검색');
      input!.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      form!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });

    expect(searchNotes).toHaveBeenCalledWith('RAG 검색');
    expect(view.querySelector('p.line-clamp-2')?.textContent).toBe('검색 근거 요약');
    expect(view.querySelector('p.line-clamp-2 mark')?.textContent).toBe('근거 요약');

    const conceptLink = view.querySelector<HTMLAnchorElement>('[aria-label="RAG 개념으로 탐색"]');
    await act(async () => {
      conceptLink!.dispatchEvent(new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        button: 0,
      }));
    });

    expect(input!.value).toBe('');
    expect(view.querySelector('p.line-clamp-2')).toBeNull();
    const returnButton = Array.from(view.querySelectorAll('button'))
      .find((button) => button.textContent?.includes('검색 결과로 돌아가기 (1)'));
    expect(returnButton).toBeDefined();

    await act(async () => {
      returnButton!.click();
    });

    expect(input!.value).toBe('RAG 검색');
    expect(view.querySelector('p.line-clamp-2')?.textContent).toBe('검색 근거 요약');
    expect(view.querySelector('p.line-clamp-2 mark')?.textContent).toBe('근거 요약');
    expect(replaceMock).toHaveBeenLastCalledWith('/notes', { scroll: false });
  });
});

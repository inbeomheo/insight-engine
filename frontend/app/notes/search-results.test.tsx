import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getNotes,
  searchNotes,
  type NoteListItem,
  type NoteSearchResult,
} from '@/lib/api';
import type { NoteFacet } from '@/lib/note-list';
import NotesPage, { ActiveFacetBar, NotesList, SearchResultsList, shouldHandleFacetLinkClick } from './page';

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

async function renderNotesList(onFacetSelect = vi.fn()) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <NotesList
        notes={[note()]}
        studyProgressByNote={{}}
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
  facetHistory = [],
  onReturnToFacet = vi.fn(),
  onReturnToSearch = vi.fn(),
  onClear = vi.fn(),
}: {
  searchReturnQuery: string | null;
  facetHistory?: NoteFacet[];
  onReturnToFacet?: (targetFacet: NoteFacet, nextHistory: NoteFacet[]) => void;
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
        facetHistory={facetHistory}
        searchReturnQuery={searchReturnQuery}
        searchReturnCount={2}
        onReturnToFacet={onReturnToFacet}
        onReturnToSearch={onReturnToSearch}
        onClear={onClear}
      />
    );
  });
  return container;
}

function findByAriaLabel<T extends Element>(
  view: ParentNode,
  selector: string,
  pattern: RegExp,
): T | null {
  return Array.from(view.querySelectorAll<T>(selector))
    .find((element) => pattern.test(element.getAttribute('aria-label') ?? '')) ?? null;
}

function findSearchEvidence(view: ParentNode): Element | null {
  return findByAriaLabel(view, '[role="group"]', /검색 근거$/);
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
    tags: ['학습'],
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

describe('NotesList', () => {
  it('keeps document navigation separate and pivots through encoded concept links', async () => {
    const onFacetSelect = vi.fn();
    const view = await renderNotesList(onFacetSelect);
    const documentLink = view.querySelector<HTMLAnchorElement>('[aria-label="검색 노트 문서 열기"]');
    const ragLink = view.querySelector<HTMLAnchorElement>('[aria-label="RAG 개념으로 계속 탐색"]');
    const vectorLink = view.querySelector<HTMLAnchorElement>('[aria-label="벡터 개념으로 계속 탐색"]');
    const tagLink = view.querySelector<HTMLAnchorElement>('[aria-label="학습 태그로 계속 탐색"]');
    const sourceLink = view.querySelector<HTMLAnchorElement>('[aria-label="직접 텍스트 출처로 계속 탐색"]');

    expect(documentLink?.getAttribute('href')).toBe('/notes/note%2Fid');
    expect(ragLink?.getAttribute('href')).toBe('/notes?concept=RAG');
    expect(vectorLink?.getAttribute('href')).toBe('/notes?concept=%EB%B2%A1%ED%84%B0');
    expect(tagLink?.getAttribute('href')).toBe('/notes?tag=%ED%95%99%EC%8A%B5');
    expect(sourceLink?.getAttribute('href')).toBe('/notes?source=%EC%A7%81%EC%A0%91+%ED%85%8D%EC%8A%A4%ED%8A%B8');
    expect(view.querySelector('a a')).toBeNull();

    const click = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0 });
    await act(async () => { vectorLink!.dispatchEvent(click); });

    expect(click.defaultPrevented).toBe(true);
    expect(onFacetSelect).toHaveBeenCalledWith({ type: 'concept', value: '벡터' });

    const ctrlClick = new MouseEvent('click', {
      bubbles: true,
      cancelable: true,
      button: 0,
      ctrlKey: true,
    });
    const keepTestInPlace = (event: MouseEvent) => event.preventDefault();
    document.addEventListener('click', keepTestInPlace);
    try {
      await act(async () => { vectorLink!.dispatchEvent(ctrlClick); });
    } finally {
      document.removeEventListener('click', keepTestInPlace);
    }
    expect(onFacetSelect).toHaveBeenCalledTimes(1);

    await act(async () => { tagLink!.click(); });
    await act(async () => { sourceLink!.click(); });
    expect(onFacetSelect).toHaveBeenNthCalledWith(2, { type: 'tag', value: '학습' });
    expect(onFacetSelect).toHaveBeenNthCalledWith(3, { type: 'source', value: '직접 텍스트' });
  });
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
    const snippet = findSearchEvidence(view);
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
    const snippet = findSearchEvidence(view);

    expect(snippet?.textContent).toBe('검색 근거 요약');
    expect(snippet?.querySelector('mark')).toBeNull();
  });
});

describe('ActiveFacetBar', () => {
  it('returns to the preserved search session while keeping the clear action', async () => {
    const onReturnToFacet = vi.fn();
    const onReturnToSearch = vi.fn();
    const onClear = vi.fn();
    const view = await renderActiveFacetBar({
      searchReturnQuery: 'RAG 검색',
      facetHistory: [
        { type: 'concept', value: '벡터' },
        { type: 'concept', value: '벡터' },
      ],
      onReturnToFacet,
      onReturnToSearch,
      onClear,
    });
    const returnButton = findByAriaLabel<HTMLButtonElement>(
      view,
      'button',
      /RAG 검색.*검색 결과 2개로 돌아가기$/,
    );
    const conceptPathButton = findByAriaLabel<HTMLButtonElement>(
      view,
      'button',
      /개념: 벡터 탐색 1단계로 돌아가기$/,
    );
    const secondConceptPathButton = findByAriaLabel<HTMLButtonElement>(
      view,
      'button',
      /개념: 벡터 탐색 2단계로 돌아가기$/,
    );
    const clearButton = findByAriaLabel<HTMLButtonElement>(view, 'button', /필터 해제$/);

    expect(view.textContent).toContain('개념: RAG');
    expect(view.textContent).toContain('1/4개 노트');
    expect(returnButton?.textContent).toContain('“RAG 검색” 검색 결과');
    expect(returnButton?.textContent).toContain('(2)');

    await act(async () => { conceptPathButton?.click(); });
    await act(async () => { secondConceptPathButton?.click(); });
    await act(async () => { returnButton?.click(); });
    await act(async () => { clearButton?.click(); });
    expect(onReturnToFacet).toHaveBeenNthCalledWith(
      1,
      { type: 'concept', value: '벡터' },
      [],
    );
    expect(onReturnToFacet).toHaveBeenNthCalledWith(
      2,
      { type: 'concept', value: '벡터' },
      [{ type: 'concept', value: '벡터' }],
    );
    expect(conceptPathButton?.className).toContain('min-h-9');
    expect(conceptPathButton?.querySelector('span')?.className).toContain('truncate');
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
  it('removes stale results when a newer search fails', async () => {
    const view = await renderNotesPage();
    const input = view.querySelector<HTMLInputElement>('input[placeholder^="노트 검색"]')!;
    const form = input.closest('form')!;
    const setValue = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      'value',
    )?.set;

    await act(async () => {
      setValue?.call(input, '첫 검색');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(findSearchEvidence(view)?.textContent).toBe('검색 근거 요약');

    vi.mocked(searchNotes).mockRejectedValueOnce(new Error('검색 서버 오류'));
    await act(async () => {
      setValue?.call(input, '실패 검색');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });

    expect(findSearchEvidence(view)).toBeNull();
    expect(view.querySelector('[role="alert"]')?.textContent).toBe('검색 서버 오류');
    expect(input.value).toBe('실패 검색');
  });

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
    expect(findSearchEvidence(view)?.textContent).toBe('검색 근거 요약');
    expect(findSearchEvidence(view)?.querySelector('mark')?.textContent).toBe('근거 요약');

    const conceptLink = view.querySelector<HTMLAnchorElement>('[aria-label="RAG 개념으로 탐색"]');
    await act(async () => {
      conceptLink!.dispatchEvent(new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        button: 0,
      }));
    });

    expect(input!.value).toBe('');
    expect(findSearchEvidence(view)).toBeNull();

    const vectorPivot = view.querySelector<HTMLAnchorElement>('[aria-label="벡터 개념으로 계속 탐색"]');
    await act(async () => {
      vectorPivot!.dispatchEvent(new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        button: 0,
      }));
    });
    expect(replaceMock).toHaveBeenLastCalledWith('/notes?concept=%EB%B2%A1%ED%84%B0', { scroll: false });

    const tagPivot = view.querySelector<HTMLAnchorElement>('[aria-label="학습 태그로 계속 탐색"]');
    await act(async () => { tagPivot!.click(); });
    expect(replaceMock).toHaveBeenLastCalledWith('/notes?tag=%ED%95%99%EC%8A%B5', { scroll: false });

    const sourcePivot = view.querySelector<HTMLAnchorElement>('[aria-label="직접 텍스트 출처로 계속 탐색"]');
    await act(async () => { sourcePivot!.click(); });
    expect(replaceMock).toHaveBeenLastCalledWith(
      '/notes?source=%EC%A7%81%EC%A0%91+%ED%85%8D%EC%8A%A4%ED%8A%B8',
      { scroll: false },
    );

    const tagPathButton = findByAriaLabel<HTMLButtonElement>(
      view,
      'button',
      /태그: 학습 탐색 3단계로 돌아가기$/,
    );
    expect(tagPathButton).not.toBeNull();
    await act(async () => { tagPathButton!.click(); });
    expect(replaceMock).toHaveBeenLastCalledWith('/notes?tag=%ED%95%99%EC%8A%B5', { scroll: false });
    expect(view.querySelector('[aria-current="page"]')?.textContent).toBe('태그: 학습');
    expect(findByAriaLabel(view, 'button', /개념: RAG 탐색 1단계로 돌아가기$/)).not.toBeNull();
    expect(findByAriaLabel(view, 'button', /개념: 벡터 탐색 2단계로 돌아가기$/)).not.toBeNull();
    expect(findByAriaLabel(view, 'button', /출처: 직접 텍스트.*돌아가기$/)).toBeNull();

    const firstConceptPathButton = findByAriaLabel<HTMLButtonElement>(
      view,
      'button',
      /개념: RAG 탐색 1단계로 돌아가기$/,
    );
    await act(async () => { firstConceptPathButton!.click(); });
    expect(replaceMock).toHaveBeenLastCalledWith('/notes?concept=RAG', { scroll: false });
    expect(view.querySelector('[aria-label="위키 탐색 경로"]')).toBeNull();

    const returnButton = findByAriaLabel<HTMLButtonElement>(
      view,
      'button',
      /RAG 검색.*검색 결과 1개로 돌아가기$/,
    );
    expect(returnButton).not.toBeNull();

    await act(async () => {
      returnButton!.click();
    });

    expect(input!.value).toBe('RAG 검색');
    expect(findSearchEvidence(view)?.textContent).toBe('검색 근거 요약');
    expect(findSearchEvidence(view)?.querySelector('mark')?.textContent).toBe('근거 요약');
    expect(replaceMock).toHaveBeenLastCalledWith('/notes', { scroll: false });
  });
});

import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getNote, type NoteDetail } from '@/lib/api';
import NoteDetailPage from './page';

const navigation = vi.hoisted(() => ({
  id: 'support',
  search: 'flow=recall&origin=origin&support=support&step=support',
}));
const store = vi.hoisted(() => ({ hydrate: vi.fn(), reports: [] }));

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: navigation.id }),
  useSearchParams: () => new URLSearchParams(navigation.search),
}));
vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));
vi.mock('@/lib/api', () => ({ getNote: vi.fn() }));
vi.mock('@/components/result/ResultChatPanel', () => ({ default: () => null }));
vi.mock('@/stores/resultStore', () => ({
  useResultStore: (selector: (state: typeof store) => unknown) => selector(store),
}));

function makeNote(id: string): NoteDetail {
  return {
    id,
    source: { type: 'text', url: '', title: id + ' 제목' },
    created_at: '2026-07-12T00:00:00.000Z',
    language: 'ko',
    tags: [],
    key_concepts: ['회상'],
    summary: '요약',
    quotes: [],
    learning_points: [],
    review_questions: [
      { question: '첫 번째 질문', answer: '첫 번째 답' },
      { question: '두 번째 질문', answer: '두 번째 답' },
    ],
    related_notes: [],
  } as NoteDetail;
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;
let scrollIntoView: ReturnType<typeof vi.fn>;

async function renderPage() {
  if (!container) {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  }
  await act(async () => {
    root!.render(<NoteDetailPage />);
    await Promise.resolve();
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function findButton(label: string): HTMLButtonElement {
  const button = Array.from(document.querySelectorAll('button')).find((item) =>
    item.textContent?.includes(label)
  );
  if (!button) throw new Error(label + ' 버튼을 찾지 못했습니다.');
  return button;
}

describe('NoteDetailPage 회상 보강 UI', () => {
  beforeEach(() => {
    navigation.id = 'support';
    navigation.search = 'flow=recall&origin=origin&support=support&step=support';
    vi.mocked(getNote).mockImplementation(async (id) => makeNote(id));
    window.localStorage.clear();
    scrollIntoView = vi.fn();
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      configurable: true,
      value: scrollIntoView,
    });
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    container?.remove();
    root = null;
    container = null;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('marks support and retry current steps and builds internal flow links', async () => {
    await renderPage();
    expect(document.querySelector('[aria-current="step"]')?.textContent).toContain('1/2 연결 노트 읽기');
    expect(document.querySelector('a[href*="step=retry"]')?.getAttribute('href')).toBe(
      '/notes/origin?flow=recall&origin=origin&support=support&step=retry#review-questions'
    );

    await act(async () => root!.unmount());
    root = null;
    container?.remove();
    container = null;
    navigation.id = 'origin';
    navigation.search = 'flow=recall&origin=origin&support=support&step=retry';
    await renderPage();

    expect(document.querySelector('[aria-current="step"]')?.textContent).toContain('2/2 원래 질문 재도전');
    expect(document.querySelector('a[href*="step=support"]')?.getAttribute('href')).toBe(
      '/notes/support?flow=recall&origin=origin&support=support&step=support'
    );
  });

  it('keeps completed questions visible in retry mode and hides every answer', async () => {
    navigation.id = 'origin';
    navigation.search = 'flow=recall&origin=origin&support=support&step=retry';
    await renderPage();

    const reviewButtons = Array.from(document.querySelectorAll('button')).filter((item) =>
      item.textContent?.includes('복습 체크')
    );
    for (const button of reviewButtons) {
      await act(async () => button.dispatchEvent(new MouseEvent('click', { bubbles: true })));
    }
    await act(async () => findButton('완료 숨기기').dispatchEvent(new MouseEvent('click', { bubbles: true })));

    expect(document.body.textContent).toContain('첫 번째 질문');
    expect(document.body.textContent).toContain('두 번째 질문');
    expect(document.body.textContent).not.toContain('첫 번째 답');
    expect(document.body.textContent).not.toContain('두 번째 답');
  });

  it('reacts to query-only changes and falls back for an invalid query', async () => {
    navigation.id = 'origin';
    navigation.search = 'flow=recall&origin=origin&support=support&step=retry';
    await renderPage();
    expect(document.body.textContent).toContain('회상 보강 2단계');

    navigation.search = 'flow=recall&origin=origin&support=support&step=retry&return=%2Fadmin';
    await renderPage();
    expect(document.body.textContent).not.toContain('회상 보강 2단계');
  });

  it('restarts retry presentation when only the support id changes', async () => {
    navigation.id = 'origin';
    navigation.search = 'flow=recall&origin=origin&support=support-a&step=retry';
    await renderPage();

    await act(async () => {
      findButton('전체 답 보기').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).toContain('첫 번째 답');
    const previousScrollCalls = scrollIntoView.mock.calls.length;

    navigation.search = 'flow=recall&origin=origin&support=support-b&step=retry';
    await renderPage();

    expect(document.body.textContent).not.toContain('첫 번째 답');
    expect(scrollIntoView.mock.calls.length).toBeGreaterThan(previousScrollCalls);
  });

  it('scrolls after retry content renders', async () => {
    navigation.id = 'origin';
    navigation.search = 'flow=recall&origin=origin&support=support&step=retry';
    await renderPage();

    expect(scrollIntoView).toHaveBeenCalledWith({ block: 'start' });
    expect((scrollIntoView.mock.instances[0] as Element).id).toBe('review-questions');
  });

  it('does not write or remove localStorage merely by entering the flow', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    const removeItem = vi.spyOn(Storage.prototype, 'removeItem');
    navigation.id = 'origin';
    navigation.search = 'flow=recall&origin=origin&support=support&step=retry';

    await renderPage();

    expect(setItem).not.toHaveBeenCalled();
    expect(removeItem).not.toHaveBeenCalled();
  });
});

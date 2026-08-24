import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Report } from '@/lib/types';
import MobileAppShell from './MobileAppShell';

// next/dynamic 은 React.lazy 기반이라 jsdom에서 로딩 타이밍이 흔들린다 → 동기 스텁으로 대체
vi.mock('next/dynamic', () => ({
  default: () => function VideoChatPanelStub() {
    return <div data-testid="video-chat-panel">영상 채팅</div>;
  },
}));
vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));
vi.mock('@/lib/api', () => ({
  createKnowledgeNote: vi.fn(),
  isApiError: () => false,
}));

const REPORT: Report = {
  id: 'report-1',
  url: 'https://www.youtube.com/watch?v=abc',
  youtube_title: '테스트 영상',
  title: '모바일 상세 리포트',
  content: '본문 내용',
  html: '<p>본문 내용</p>',
  style: 'summary',
  prompt: '',
  usage: { total_tokens: 100 },
  elapsed_time: 1,
  transcript_source: 'api',
  cached: false,
  comment_summary_included: false,
  time: '2026-08-24 10:00',
  createdAt: 1756000000000,
};

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function renderShell() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <MobileAppShell
        reports={[REPORT]}
        urls={[]}
        isLoading={false}
        error={null}
        onAddUrl={() => null}
        onRemoveUrl={() => {}}
        onGenerate={() => {}}
        inputTab="url"
        onInputTabChange={() => {}}
        textValue=""
        onTextChange={() => {}}
        onGenerateText={() => {}}
      />
    );
  });
}

function findByText(selector: string, text: string): HTMLElement {
  const el = Array.from(document.querySelectorAll<HTMLElement>(selector)).find(
    (node) => node.textContent?.includes(text),
  );
  if (!el) throw new Error(`"${text}" 요소를 찾지 못했습니다 (${selector})`);
  return el;
}

async function click(el: HTMLElement) {
  await act(async () => {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

beforeEach(() => {
  container = null;
  root = null;
});

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
});

describe('MobileAppShell', () => {
  it('하단 nav가 safe-area(홈 인디케이터) 여백을 확보한다', async () => {
    await renderShell();
    const nav = document.querySelector('nav[aria-label="모바일 하단 네비게이션"]');
    expect(nav).not.toBeNull();
    // 노치/홈 인디케이터 영역에 버튼이 걸치지 않도록 env(safe-area-inset-*)를 반영해야 한다
    expect(nav!.className).toContain('env(safe-area-inset-bottom)');
    expect(nav!.className).toContain('env(safe-area-inset-left)');
  });

  it('활성 탭에만 aria-current를 표시하고 탭 전환이 동작한다', async () => {
    await renderShell();
    const tabs = () =>
      Array.from(document.querySelectorAll<HTMLButtonElement>(
        'nav[aria-label="모바일 하단 네비게이션"] button',
      ));

    expect(tabs().map((b) => b.getAttribute('aria-current'))).toEqual(['page', null, null]);

    await click(tabs()[1]);
    expect(tabs().map((b) => b.getAttribute('aria-current'))).toEqual([null, 'page', null]);
    expect(document.body.textContent).toContain('라이브러리');
  });

  it('라이브러리 카드를 열면 상세에서 "영상에 질문하기"를 열 수 있다', async () => {
    await renderShell();
    const navTabs = Array.from(document.querySelectorAll<HTMLButtonElement>(
      'nav[aria-label="모바일 하단 네비게이션"] button',
    ));
    await click(navTabs[1]);

    await click(findByText('section button', REPORT.title));
    expect(document.body.textContent).toContain(REPORT.title);

    // 상단 액션(아이콘)과 본문 CTA 두 곳 모두에서 접근 가능해야 한다
    const askButtons = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).filter(
      (b) => b.getAttribute('aria-label') === '영상에 질문하기' || b.textContent?.includes('영상에 질문하기'),
    );
    expect(askButtons.length).toBeGreaterThanOrEqual(2);

    expect(document.querySelector('[data-testid="video-chat-panel"]')).toBeNull();
    await click(askButtons[0]);
    expect(document.querySelector('[data-testid="video-chat-panel"]')).not.toBeNull();
  });
});

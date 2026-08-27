import { act, useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Report } from '@/lib/types';
import { STORAGE_KEYS } from '@/lib/constants';
import { useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import MobileAppShell from './MobileAppShell';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// next/dynamic 은 React.lazy 기반이라 jsdom에서 로딩 타이밍이 흔들린다 → 동기 스텁으로 대체
vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<unknown>) => loader.toString().includes('ContentEditor')
    ? function ContentEditorStub({ onSave }: { onSave: (draft: { title: string; content: string }) => void | Promise<void> }) {
        return (
          <div data-testid="content-editor">
            문서 편집기
            <button type="button" onClick={() => void onSave({ title: '영속화된 모바일 제목', content: '영속화된 모바일 본문' })}>
              편집 저장 테스트
            </button>
          </div>
        );
      }
    : function VideoChatPanelStub() {
        return <div data-testid="video-chat-panel">영상 채팅</div>;
      },
}));
vi.mock('next/link', () => ({
  default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div>{children}</div>,
}));
vi.mock('@/lib/api', () => ({
  createKnowledgeNote: vi.fn(),
  isApiError: () => false,
}));
vi.mock('@/lib/markdown-to-html', () => ({
  markdownToHtml: vi.fn(async (content: string) => `<p>${content}</p>`),
}));
vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => ({
      'result.edit': '문서 편집',
      'result.editStreaming': '스트리밍 중입니다.',
      'result.editConflict': '편집 충돌',
      'result.editEmptyTitle': '제목 필요',
      'result.editEmptyContent': '본문 필요',
      'result.editNoChange': '변경 없음',
      'result.editStorageFailed': '저장소 실패',
      'result.editSaved': '저장 완료',
      'result.editSaveFailed': '저장 실패',
    }[key] ?? key),
  }),
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

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

let root: Root | null = null;
let container: HTMLDivElement | null = null;

interface RenderShellOptions {
  activeReportId?: string | null;
  reports?: Report[];
  urls?: string[];
  onGenerate?: (draftUrl?: string) => void;
  onOpenSettings?: () => void;
  onReportOpened?: (reportId: string) => void;
}

async function renderShell(options: RenderShellOptions = {}) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);

  function Harness() {
    const [activeReportId, setActiveReportId] = useState<string | null>(options.activeReportId ?? null);
    return (
      <MobileAppShell
        reports={options.reports ?? [REPORT]}
        activeReportId={activeReportId}
        onActiveReportIdChange={setActiveReportId}
        onReportOpened={options.onReportOpened ?? (() => {})}
        onOpenSettings={options.onOpenSettings ?? (() => {})}
        urls={options.urls ?? []}
        isLoading={false}
        error={null}
        onAddUrl={() => null}
        onRemoveUrl={() => {}}
        onGenerate={options.onGenerate ?? (() => {})}
        inputTab="url"
        onInputTabChange={() => {}}
        textValue=""
        onTextChange={() => {}}
        onGenerateText={() => {}}
      />
    );
  }

  await act(async () => {
    root!.render(<Harness />);
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
    await Promise.resolve();
  });
}

beforeEach(() => {
  setAuthSession(null);
  container = null;
  root = null;
  useSettingsStore.setState({ generationMode: 'individual' });
  useResultStore.setState({ reports: [REPORT] });
  localStorage.setItem(STORAGE_KEYS.REPORTS, JSON.stringify([REPORT]));
});

afterEach(() => {
  act(() => root?.unmount());
  setAuthSession(null);
  container?.remove();
});

describe('MobileAppShell', () => {
  it('계정 전환 시 모바일 미제출 URL 초안을 즉시 비운다', async () => {
    setAuthSession(authSession('account-a'));
    await renderShell();
    const draft = document.querySelector<HTMLInputElement>('input[aria-label="분석할 URL 입력"]')!;

    await act(async () => {
      draft.value = 'https://a.example/draft';
      draft.dispatchEvent(new Event('input', { bubbles: true }));
    });
    expect(document.querySelector<HTMLInputElement>('input[aria-label="분석할 URL 입력"]')?.value)
      .toBe('https://a.example/draft');

    await act(async () => setAuthSession(authSession('account-b')));
    expect(document.querySelector<HTMLInputElement>('input[aria-label="분석할 URL 입력"]')?.value)
      .toBe('');
  });

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

  it('activeReportId 딥링크 대상 상세를 열고 마운트된 뒤 완료를 알린다', async () => {
    const onReportOpened = vi.fn();
    await renderShell({ activeReportId: REPORT.id, onReportOpened });

    expect(document.body.textContent).toContain(REPORT.title);
    expect(onReportOpened).toHaveBeenCalledWith(REPORT.id);
  });

  it('전체 Report 객체를 보관하지 않고 activeReportId로 최신 보고서를 다시 찾는다', async () => {
    function UpdatingHarness() {
      const [reports, setReports] = useState([REPORT]);
      return (
        <>
          <button type="button" onClick={() => setReports([{ ...REPORT, title: '수정된 모바일 제목' }])}>
            보고서 갱신
          </button>
          <MobileAppShell
            reports={reports}
            activeReportId={REPORT.id}
            onActiveReportIdChange={() => {}}
            onReportOpened={() => {}}
            onOpenSettings={() => {}}
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
        </>
      );
    }

    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => root!.render(<UpdatingHarness />));
    await click(findByText('button', '보고서 갱신'));

    expect(document.body.textContent).toContain('수정된 모바일 제목');
  });

  it.each([
    ['combined', '통합'],
    ['fusion', '퓨전'],
  ] as const)('%s 모드는 URL이 1개면 명시 오류와 비활성 버튼을 표시한다', async (mode, label) => {
    const onGenerate = vi.fn();
    useSettingsStore.setState({ generationMode: mode });
    await renderShell({ urls: ['https://example.com/one'], onGenerate });

    const generateButton = findByText('button', '콘텐츠 생성') as HTMLButtonElement;
    expect(generateButton.disabled).toBe(true);
    expect(document.querySelector('[role="alert"]')?.textContent).toContain(`${label} 모드는 URL 2개 이상이 필요합니다.`);
    await click(generateButton);
    expect(onGenerate).not.toHaveBeenCalled();
  });

  it('모바일 생성 화면에서 설정 모달 진입 콜백을 제공한다', async () => {
    const onOpenSettings = vi.fn();
    await renderShell({ onOpenSettings });

    await click(document.querySelector<HTMLButtonElement>('button[aria-label="설정 열기"]')!);
    expect(onOpenSettings).toHaveBeenCalledTimes(1);
  });

  it('모바일 상세에서 문서 편집기로 진입할 수 있다', async () => {
    await renderShell({ activeReportId: REPORT.id });

    await click(document.querySelector<HTMLButtonElement>('button[aria-label="문서 편집"]')!);
    expect(document.querySelector('[data-testid="content-editor"]')).not.toBeNull();
  });

  it('html이 빈 완료 평문 보고서도 모바일에서 편집할 수 있다', async () => {
    const completedPlainReport = {
      ...REPORT,
      content: 'html이 없는 완료 평문',
      html: '',
      is_streaming: false,
    };
    useResultStore.setState({ reports: [completedPlainReport] });
    await renderShell({ activeReportId: REPORT.id, reports: [completedPlainReport] });

    const editButton = document.querySelector<HTMLButtonElement>('button[aria-label="문서 편집"]');
    expect(editButton?.disabled).toBe(false);
    await click(editButton!);
    expect(document.querySelector('[data-testid="content-editor"]')).not.toBeNull();
  });

  it('is_streaming이 true인 임시 보고서만 모바일 편집을 막는다', async () => {
    const streamingReport = { ...REPORT, is_streaming: true };
    useResultStore.setState({ reports: [streamingReport] });
    await renderShell({ activeReportId: REPORT.id, reports: [streamingReport] });

    expect(document.querySelector<HTMLButtonElement>(
      'button[aria-label="문서 편집"]',
    )?.disabled).toBe(true);
  });

  it('모바일 문서 편집은 성공 알림 전에 localStorage에 즉시 영속화한다', async () => {
    await renderShell({ activeReportId: REPORT.id });

    await click(document.querySelector<HTMLButtonElement>('button[aria-label="문서 편집"]')!);
    await click(findByText('button', '편집 저장 테스트'));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEYS.REPORTS) || '[]') as Report[];
    expect(stored[0]).toMatchObject({
      id: REPORT.id,
      title: '영속화된 모바일 제목',
      content: '영속화된 모바일 본문',
    });
  });

  it('모바일 문서 편집은 이전 공유 URL을 메모리와 localStorage에서 무효화한다', async () => {
    const sharedReport = { ...REPORT, share_url: 'https://share.example/stale' };
    useResultStore.setState({ reports: [sharedReport] });
    localStorage.setItem(STORAGE_KEYS.REPORTS, JSON.stringify([sharedReport]));
    await renderShell({ activeReportId: REPORT.id, reports: [sharedReport] });

    await click(document.querySelector<HTMLButtonElement>('button[aria-label="문서 편집"]')!);
    await click(findByText('button', '편집 저장 테스트'));
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(useResultStore.getState().reports[0].share_url).toBeUndefined();
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEYS.REPORTS) || '[]') as Report[];
    expect(stored[0].share_url).toBeUndefined();
  });
});

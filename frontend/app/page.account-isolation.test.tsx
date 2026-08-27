import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import { useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useUIStore } from '@/stores/uiStore';
import type { Report } from '@/lib/types';
import { getStorageAccountNamespace, saveReports } from '@/lib/storage';
import Home from './page';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const {
  generateBatchUrlsMock,
  generateFusionUrlsMock,
  generateFromTextMock,
  generateMergedUrlsMock,
  reportRenders,
} = vi.hoisted(() => ({
  generateBatchUrlsMock: vi.fn(),
  generateFusionUrlsMock: vi.fn(),
  generateFromTextMock: vi.fn(),
  generateMergedUrlsMock: vi.fn(),
  reportRenders: [] as Array<{ userId: string | null; title: string }>,
}));

vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<unknown>) => loader.toString().includes('ResultCard')
    ? function ResultCardProbe({ report }: { report: { title: string } }) {
        let userId: string | null = null;
        try {
          const raw = localStorage.getItem('insight-engine-auth-session');
          userId = raw ? JSON.parse(raw).user?.id ?? null : null;
        } catch {
          userId = null;
        }
        reportRenders.push({ userId, title: report.title });
        return <article data-testid="result-card-probe">{report.title}</article>;
      }
    : function DynamicStub() {
        return null;
      },
}));

vi.mock('@/components/layout/Sidebar', () => ({ default: () => null }));
vi.mock('@/components/input/ClipboardPaste', () => ({ default: () => null }));
vi.mock('@/components/settings/SettingsPopover', () => ({ default: () => null }));
vi.mock('@/components/settings/SettingsModal', () => ({ default: () => null }));
vi.mock('@/components/result/ViewModeSelector', () => ({ default: () => null }));
vi.mock('@/components/result/FilterBar', () => ({ default: () => null }));
vi.mock('@/components/result/LoadingSkeleton', () => ({ default: () => null }));
vi.mock('@/components/result/FusionProgress', () => ({ default: () => null }));
vi.mock('@/components/ui/scroll-area', () => ({
  ScrollArea: ({ children }: React.PropsWithChildren) => <div>{children}</div>,
}));
vi.mock('@/components/mobile/MobileAppShell', () => ({
  default: ({
    urls,
    inputTab,
    textValue,
  }: {
    urls: string[];
    inputTab: string;
    textValue: string;
  }) => (
    <output
      data-testid="mobile-source-state"
      data-input-tab={inputTab}
      data-text-value={textValue}
      data-urls={urls.join(',')}
    />
  ),
}));
vi.mock('@/hooks/useProviders', () => ({ useProviders: () => undefined }));
vi.mock('@/hooks/useGenerate', () => ({
  useGenerate: () => ({
    isLoading: false,
    error: null,
    generateBatchUrls: generateBatchUrlsMock,
    generateMergedUrls: generateMergedUrlsMock,
    generateFusionUrls: generateFusionUrlsMock,
    generateFromText: generateFromTextMock,
  }),
}));
vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key === 'emptyState.description' ? '설명' : key,
  }),
}));
vi.mock('@/lib/storage', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/storage')>();
  return { ...actual, isOnboardingDone: () => true };
});

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

const ACCOUNT_A_REPORT: Report = {
  id: 'account-a-report',
  url: 'https://a.example/report',
  youtube_title: 'A 영상',
  title: 'A 계정 보고서',
  content: 'A 계정 본문',
  html: '<p>A</p>',
  style: 'summary',
  prompt: '',
  usage: { total_tokens: 1 },
  elapsed_time: 1,
  transcript_source: 'test',
  cached: false,
  comment_summary_included: false,
  time: '2026-08-28 00:00',
  createdAt: 1,
};

async function typeInto(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const prototype = element instanceof HTMLInputElement
    ? HTMLInputElement.prototype
    : HTMLTextAreaElement.prototype;
  const valueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;
  await act(async () => {
    valueSetter?.call(element, value);
    element.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

async function addDesktopUrl(url: string) {
  const input = document.querySelector<HTMLInputElement>('#url-input')!;
  await typeInto(input, url);
  await act(async () => {
    const addButton = document.querySelector<HTMLButtonElement>('button[aria-label="URL 추가"]');
    if (!addButton) throw new Error('URL 입력 후 추가 버튼으로 전환되지 않았습니다.');
    addButton.click();
  });
}

function findButton(label: string): HTMLButtonElement {
  const button = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
    (candidate) => candidate.textContent?.trim() === label,
  );
  if (!button) throw new Error(`"${label}" 버튼을 찾지 못했습니다.`);
  return button;
}

describe('Home 계정 전환 입력 격리', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    setAuthSession(null);
    localStorage.clear();
    useResultStore.setState({
      reports: [],
      searchQuery: '',
      styleFilter: '',
      pinnedIds: new Set<string>(),
    });
    useSettingsStore.setState({
      selectedModel: 'test-model',
      selectedStyle: 'summary',
      generationMode: 'individual',
      enableAgentMode: false,
    });
    useUIStore.setState({ activeReportId: null, activeModal: null });
    generateBatchUrlsMock.mockReset().mockResolvedValue(true);
    generateFusionUrlsMock.mockReset().mockResolvedValue(true);
    generateFromTextMock.mockReset().mockResolvedValue(true);
    generateMergedUrlsMock.mockReset().mockResolvedValue(true);
    reportRenders.length = 0;
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    setAuthSession(null);
    localStorage.clear();
    container.remove();
    vi.clearAllMocks();
  });

  it('A의 URL 큐·붙여넣은 텍스트·텍스트 탭을 B 전환 시 비운다', async () => {
    setAuthSession(authSession('account-a'));
    await act(async () => root.render(<Home />));

    await addDesktopUrl('https://a.example/video');
    const draftUrl = document.querySelector<HTMLInputElement>('#url-input')!;
    await typeInto(draftUrl, 'https://a.example/unsubmitted');
    await act(async () => findButton('텍스트 붙여넣기').click());
    const textArea = document.querySelector<HTMLTextAreaElement>(
      'textarea[placeholder^="분석할 텍스트"]',
    )!;
    await typeInto(textArea, 'A 계정의 미제출 텍스트');

    expect(document.querySelector('[data-testid="mobile-source-state"]')?.getAttribute('data-urls'))
      .toContain('https://a.example/video');
    expect(draftUrl.value).toBe('https://a.example/unsubmitted');
    expect(textArea.value).toBe('A 계정의 미제출 텍스트');
    expect(findButton('텍스트 붙여넣기').getAttribute('aria-pressed')).toBe('true');

    await act(async () => setAuthSession(authSession('account-b')));
    await vi.waitFor(() => {
      expect(document.querySelector<HTMLInputElement>('#url-input')?.value).toBe('');
      expect(document.querySelector<HTMLTextAreaElement>(
        'textarea[placeholder^="분석할 텍스트"]',
      )?.value).toBe('');
      expect(findButton('URL 입력').getAttribute('aria-pressed')).toBe('true');
    });

    const mobileState = document.querySelector('[data-testid="mobile-source-state"]');
    expect(mobileState?.getAttribute('data-input-tab')).toBe('url');
    expect(mobileState?.getAttribute('data-text-value')).toBe('');
    expect(mobileState?.getAttribute('data-urls')).toBe('');
  });

  it('계정 전환 렌더에서 A 보고서를 B ResultCard에 전달하지 않는다', async () => {
    saveReports([ACCOUNT_A_REPORT], getStorageAccountNamespace('account-a'));
    saveReports([], getStorageAccountNamespace('account-b'));
    setAuthSession(authSession('account-a'));
    useResultStore.setState({ reports: [ACCOUNT_A_REPORT] });
    await act(async () => root.render(<Home />));
    await vi.waitFor(() => {
      expect(reportRenders.some(({ userId, title }) =>
        userId === 'account-a' && title === ACCOUNT_A_REPORT.title)).toBe(true);
    });

    const switchRenderStart = reportRenders.length;
    await act(async () => setAuthSession(authSession('account-b')));
    await vi.waitFor(() => {
      expect(useResultStore.getState().reports).toEqual([]);
    });

    expect(reportRenders.slice(switchRenderStart)).not.toContainEqual({
      userId: 'account-b',
      title: ACCOUNT_A_REPORT.title,
    });
    expect(document.body.textContent).not.toContain(ACCOUNT_A_REPORT.title);
  });

  it('A의 늦은 생성 후 제거 콜백이 B URL 큐를 삭제하지 않는다', async () => {
    const pending = deferred<boolean>();
    generateBatchUrlsMock.mockImplementationOnce(() => pending.promise);
    setAuthSession(authSession('account-a'));
    await act(async () => root.render(<Home />));
    await addDesktopUrl('https://a.example/video');

    const generateButton = Array.from(document.querySelectorAll<HTMLButtonElement>('button')).find(
      (button) => button.textContent?.includes('콘텐츠 생성'),
    )!;
    await act(async () => generateButton.click());
    expect(generateBatchUrlsMock).toHaveBeenCalledWith(['https://a.example/video']);

    await act(async () => setAuthSession(authSession('account-b')));
    await addDesktopUrl('https://b.example/video');
    expect(document.querySelector('[data-testid="mobile-source-state"]')?.getAttribute('data-urls'))
      .toBe('https://b.example/video');

    await act(async () => {
      pending.resolve(true);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(document.querySelector('[data-testid="mobile-source-state"]')?.getAttribute('data-urls'))
      .toBe('https://b.example/video');
  });
});

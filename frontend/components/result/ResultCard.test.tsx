import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/lib/i18n/I18nProvider';
import { createReport } from '@/lib/report-factory';
import { STORAGE_KEYS } from '@/lib/constants';
import { createSharePage } from '@/lib/api';
import type { Report } from '@/lib/types';
import { useResultStore } from '@/stores/resultStore';
import { TooltipProvider } from '@/components/ui/tooltip';
import { toast } from 'sonner';
import {
  default as ResultCard,
  startNotebookLmStatusPolling,
  type NotebookLmPollJob,
} from './ResultCard';

vi.mock('next/dynamic', () => ({
  default: (loader: () => Promise<unknown>) => loader.toString().includes('ContentEditor')
    ? function ContentEditorStub({ onSave }: { onSave: (draft: { title: string; content: string }) => void | Promise<void> }) {
        return (
          <button
            type="button"
            data-testid="desktop-edit-save"
            onClick={() => void onSave({ title: '수정된 데스크톱 제목', content: '수정된 데스크톱 본문' })}
          >
            편집 저장 테스트
          </button>
        );
      }
    : function DynamicStub() {
        return null;
      },
}));
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock('@/lib/markdown-to-html', () => ({
  injectTimestampLinks: (content: string) => content,
  markdownToHtml: vi.fn(async (content: string) => `<p>${content}</p>`),
}));
vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    createSharePage: vi.fn(),
  };
});
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe('NotebookLM 상태 폴링', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('응답이 끝나기 전에 다음 상태 요청을 겹쳐 보내지 않는다', async () => {
    const pending = deferred<{ status: string }>();
    const fetchStatus = vi.fn(() => pending.promise);
    const jobs = new Map<string, NotebookLmPollJob>();

    startNotebookLmStatusPolling({
      artifactId: 'artifact-1',
      jobs,
      fetchStatus,
      onTerminal: vi.fn(),
      onTimeout: vi.fn(),
      onFailure: vi.fn(),
      intervalMs: 100,
    });

    await vi.advanceTimersByTimeAsync(100);
    expect(fetchStatus).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(500);
    expect(fetchStatus).toHaveBeenCalledTimes(1);

    pending.resolve({ status: 'in_progress' });
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(100);
    expect(fetchStatus).toHaveBeenCalledTimes(2);
  });

  it('같은 artifact의 취소된 이전 응답이 새 폴링 완료를 덮어쓰지 않는다', async () => {
    const stale = deferred<{ status: string }>();
    const jobs = new Map<string, NotebookLmPollJob>();
    const onTerminal = vi.fn();

    startNotebookLmStatusPolling({
      artifactId: 'artifact-1',
      jobs,
      fetchStatus: vi.fn(() => stale.promise),
      onTerminal,
      onTimeout: vi.fn(),
      onFailure: vi.fn(),
      intervalMs: 100,
    });
    await vi.advanceTimersByTimeAsync(100);

    startNotebookLmStatusPolling({
      artifactId: 'artifact-1',
      jobs,
      fetchStatus: vi.fn(async () => ({ status: 'completed' })),
      onTerminal,
      onTimeout: vi.fn(),
      onFailure: vi.fn(),
      intervalMs: 100,
    });

    stale.resolve({ status: 'failed' });
    await Promise.resolve();
    expect(onTerminal).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(100);
    expect(onTerminal).toHaveBeenCalledTimes(1);
    expect(onTerminal).toHaveBeenCalledWith('completed', undefined);
  });

  it('일시적인 상태 조회 오류는 재시도한 뒤 완료 처리한다', async () => {
    const jobs = new Map<string, NotebookLmPollJob>();
    const fetchStatus = vi.fn()
      .mockRejectedValueOnce(new Error('temporary network error'))
      .mockResolvedValueOnce({ status: 'completed' });
    const onTerminal = vi.fn();
    const onFailure = vi.fn();

    startNotebookLmStatusPolling({
      artifactId: 'artifact-1',
      jobs,
      fetchStatus,
      onTerminal,
      onTimeout: vi.fn(),
      onFailure,
      intervalMs: 100,
      maxConsecutiveErrors: 3,
    });

    await vi.advanceTimersByTimeAsync(100);
    expect(fetchStatus).toHaveBeenCalledTimes(1);
    expect(onFailure).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(100);
    expect(fetchStatus).toHaveBeenCalledTimes(2);
    expect(onTerminal).toHaveBeenCalledWith('completed', undefined);
    expect(onFailure).not.toHaveBeenCalled();
  });

  it('연속 상태 조회 오류가 상한에 도달하면 한 번만 실패 처리한다', async () => {
    const jobs = new Map<string, NotebookLmPollJob>();
    const fetchStatus = vi.fn(async () => {
      throw new Error('offline');
    });
    const onFailure = vi.fn();

    startNotebookLmStatusPolling({
      artifactId: 'artifact-1',
      jobs,
      fetchStatus,
      onTerminal: vi.fn(),
      onTimeout: vi.fn(),
      onFailure,
      intervalMs: 100,
      maxConsecutiveErrors: 3,
    });

    await vi.advanceTimersByTimeAsync(300);
    expect(fetchStatus).toHaveBeenCalledTimes(3);
    expect(onFailure).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(500);
    expect(fetchStatus).toHaveBeenCalledTimes(3);
    expect(onFailure).toHaveBeenCalledTimes(1);
  });
});

describe('ResultCard 문서 편집', () => {
  let root: Root | null = null;
  let container: HTMLDivElement | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn(async () => undefined) },
    });
  });

  afterEach(() => {
    act(() => root?.unmount());
    container?.remove();
    root = null;
    container = null;
    localStorage.clear();
  });

  it('html이 빈 완료 마크다운 보고서도 편집할 수 있다', async () => {
    const report = createReport({
      id: 'markdown-report',
      is_streaming: false,
      url: '',
      title: '마크다운 완료',
      content: '# html 없는 완료 결과',
      html: '',
      style: 'summary',
    });
    useResultStore.setState({ reports: [report] });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root!.render(
        <I18nProvider>
          <TooltipProvider>
            <ResultCard report={report} />
          </TooltipProvider>
        </I18nProvider>,
      );
    });

    const editButton = container.querySelector<HTMLButtonElement>(
      'button[aria-label="문서 편집"]',
    );
    expect(editButton?.disabled).toBe(false);
    await act(async () => {
      editButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(container.querySelector('[data-testid="desktop-edit-save"]')).not.toBeNull();
  });

  it('is_streaming이 true인 임시 보고서만 편집을 막는다', async () => {
    const report = createReport({
      id: 'streaming-report',
      is_streaming: true,
      url: '',
      title: '생성 중',
      content: '생성 중인 본문',
      html: '<p>이 필드로 추론하지 않음</p>',
      style: 'summary',
    });
    useResultStore.setState({ reports: [report] });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root!.render(
        <I18nProvider>
          <TooltipProvider>
            <ResultCard report={report} />
          </TooltipProvider>
        </I18nProvider>,
      );
    });

    expect(container.querySelector<HTMLButtonElement>(
      'button[aria-label="문서 편집"]',
    )?.disabled).toBe(true);
  });

  it('내용 변경 시 이전 공유 URL을 메모리와 localStorage에서 무효화한다', async () => {
    const report = createReport({
      id: 'desktop-report',
      url: 'https://youtu.be/abcdefghijk',
      title: '원본 제목',
      content: '원본 본문',
      html: '<p>원본 본문</p>',
      style: 'summary',
      share_url: 'https://share.example/stale',
    });
    useResultStore.setState({ reports: [report] });
    localStorage.setItem(STORAGE_KEYS.REPORTS, JSON.stringify([report]));
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root!.render(
        <I18nProvider>
          <TooltipProvider>
            <ResultCard report={report} />
          </TooltipProvider>
        </I18nProvider>,
      );
    });

    const editButton = document.querySelector<HTMLButtonElement>('button[aria-label="문서 편집"]');
    expect(editButton).not.toBeNull();
    await act(async () => {
      editButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const saveButton = document.querySelector<HTMLButtonElement>('[data-testid="desktop-edit-save"]');
    expect(saveButton).not.toBeNull();
    await act(async () => {
      saveButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(useResultStore.getState().reports[0]).toMatchObject({
      title: '수정된 데스크톱 제목',
      content: '수정된 데스크톱 본문',
    });
    expect(useResultStore.getState().reports[0].share_url).toBeUndefined();
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEYS.REPORTS) || '[]') as Report[];
    expect(stored[0].share_url).toBeUndefined();
  });

  it('편집 중 문서가 갱신되면 오래된 초안으로 새 본문을 덮어쓰지 않는다', async () => {
    const original = createReport({
      id: 'concurrent-report',
      url: 'https://youtu.be/abcdefghijk',
      title: '원본 제목',
      content: '원본 본문',
      html: '<p>원본 본문</p>',
      style: 'summary',
    });
    useResultStore.setState({ reports: [original] });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    const renderCard = async (report: Report) => {
      await act(async () => {
        root!.render(
          <I18nProvider>
            <TooltipProvider>
              <ResultCard report={report} />
            </TooltipProvider>
          </I18nProvider>,
        );
      });
    };

    await renderCard(original);
    const editButton = container.querySelector<HTMLButtonElement>(
      'button[aria-label="문서 편집"]',
    );
    await act(async () => {
      editButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const updated = {
      ...original,
      content: '스트리밍으로 도착한 최신 본문',
      html: '<p>스트리밍으로 도착한 최신 본문</p>',
    };
    useResultStore.setState({ reports: [updated] });
    await renderCard(updated);

    const saveButton = container.querySelector<HTMLButtonElement>(
      '[data-testid="desktop-edit-save"]',
    );
    await act(async () => {
      saveButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await Promise.resolve();
    });

    expect(useResultStore.getState().reports[0].content).toBe(
      '스트리밍으로 도착한 최신 본문',
    );
  });

  it('공유 응답 전에 문서가 바뀌면 오래된 공유 URL을 다시 연결하지 않는다', async () => {
    const pendingShare = deferred<Awaited<ReturnType<typeof createSharePage>>>();
    vi.mocked(createSharePage).mockReturnValue(pendingShare.promise);
    const report = createReport({
      id: 'share-race-report',
      url: 'https://youtu.be/abcdefghijk',
      title: '공유 전 제목',
      content: '공유 전 본문',
      html: '<p>공유 전 본문</p>',
      style: 'summary',
    });
    useResultStore.setState({ reports: [report] });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root!.render(
        <I18nProvider>
          <TooltipProvider>
            <ResultCard report={report} />
          </TooltipProvider>
        </I18nProvider>,
      );
    });

    const shareButton = container.querySelector<HTMLButtonElement>(
      'button[aria-label="공유 페이지 만들고 링크 복사"]',
    );
    const editButton = container.querySelector<HTMLButtonElement>(
      'button[aria-label="문서 편집"]',
    );
    await act(async () => {
      shareButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await Promise.resolve();
    });
    expect(editButton?.disabled).toBe(true);

    // 다른 화면이나 동기화가 같은 보고서를 편집한 상황을 재현한다.
    useResultStore.setState({
      reports: [{
        ...report,
        title: '공유 중 바뀐 제목',
        content: '공유 중 바뀐 본문',
        html: '<p>공유 중 바뀐 본문</p>',
      }],
    });

    await act(async () => {
      pendingShare.resolve({
        id: 'stale-share',
        share_url: 'https://share.example/stale',
        title: '공유 전 제목',
        created_at: '2026-08-28T00:00:00Z',
      });
      await pendingShare.promise;
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(useResultStore.getState().reports[0]).toMatchObject({
      title: '공유 중 바뀐 제목',
      content: '공유 중 바뀐 본문',
    });
    expect(useResultStore.getState().reports[0].share_url).toBeUndefined();
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalled();
  });
});

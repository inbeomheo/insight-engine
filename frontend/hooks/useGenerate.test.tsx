import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { generate, generateStream, generateBatch, generateMerged } from '@/lib/api';
import type { GenerateResponse, StreamEvent } from '@/lib/types';
import { toast } from 'sonner';
import { useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useGenerate } from './useGenerate';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

vi.mock('@/lib/api', () => ({
  generate: vi.fn(),
  generateStream: vi.fn(),
  generateBatch: vi.fn(),
  generateMerged: vi.fn(),
  generateFusion: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    warning: vi.fn(),
  },
}));

type GenerateHook = ReturnType<typeof useGenerate>;
type BatchOutcome = Awaited<ReturnType<GenerateHook['generateBatchUrls']>>;

const RESPONSE: GenerateResponse = {
  title: '생성 결과', content: '생성 본문', html: '<p>생성 본문</p>',
  usage: { total_tokens: 1 }, elapsed_time: 1, prompt: '',
};

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

let root: Root | null = null;
let currentHook: GenerateHook | null = null;

function Harness({ onRender }: { onRender: (hook: GenerateHook) => void }) {
  const hook = useGenerate();
  useEffect(() => onRender(hook), [hook, onRender]);
  return null;
}

async function renderHook() {
  const el = document.createElement('div');
  document.body.appendChild(el);
  root = createRoot(el);
  await act(async () => {
    root!.render(<Harness onRender={(hook) => { currentHook = hook; }} />);
  });
  return {
    get hook() {
      if (!currentHook) throw new Error('hook not rendered');
      return currentHook;
    },
  };
}

function mockStream(events: StreamEvent[]) {
  vi.mocked(generateStream).mockImplementation(async (_req, onEvent) => {
    events.forEach(onEvent);
  });
}

describe('useGenerate 스트리밍 UX', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      cb(0);
      return 1;
    });
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
    vi.stubGlobal('requestIdleCallback', (cb: IdleRequestCallback) => {
      cb({ didTimeout: false, timeRemaining: () => 0 } as IdleDeadline);
      return 0;
    });
    setAuthSession(null);
    window.localStorage.clear();
    useResultStore.setState({
      reports: [],
      searchQuery: '',
      styleFilter: '',
      pinnedIds: new Set<string>(),
    });
    useSettingsStore.setState({
      selectedModel: 'gpt-test',
      selectedStyle: 'blog_seo',
      modifiers: { length: 'medium', writing_style: 'conversational', language: 'ko' },
      enableWebSearch: false,
      enableAgentMode: false,
      detailLevel: 'standard',
      transcriptLanguage: null,
    });
    currentHook = null;
  });

  afterEach(async () => {
    if (root) {
      await act(async () => root!.unmount());
      root = null;
    }
    setAuthSession(null);
    document.body.innerHTML = '';
    currentHook = null;
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it.each([
    ['URL', async (hook: GenerateHook) => { await hook.generateSingle('https://youtu.be/abc', true); }],
    ['텍스트', async (hook: GenerateHook) => { await hook.generateFromText('직접 입력', true); }],
  ])('%s 스트림 오류 시 빈 임시 카드를 제거한다', async (_label, run) => {
    mockStream([{ type: 'meta' }, { type: 'error', error: '테스트 실패' }]);
    const rendered = await renderHook();

    await act(async () => {
      await run(rendered.hook);
    });

    expect(useResultStore.getState().reports).toHaveLength(0);
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBe('테스트 실패');
  });

  it('일부 본문 수신 후 오류가 나면 본문을 유지하고 스트리밍 상태를 종료한다', async () => {
    mockStream([
      { type: 'delta', delta: '일부까지 생성된 본문' },
      { type: 'error', error: '중간 실패' },
    ]);
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.generateSingle('https://youtu.be/partial-error', true);
    });

    expect(useResultStore.getState().reports).toHaveLength(1);
    expect(useResultStore.getState().reports[0]).toMatchObject({
      title: '생성 실패',
      content: '일부까지 생성된 본문',
      is_streaming: false,
    });
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBe('중간 실패');
  });

  it('일부 본문 수신 중에는 스트리밍으로 표시하고 취소 후에는 본문을 유지한 채 종료한다', async () => {
    let resolveStarted: () => void = () => undefined;
    const started = new Promise<void>((resolve) => {
      resolveStarted = resolve;
    });

    vi.mocked(generateStream).mockImplementation(async (_req, onEvent, signal) => {
      onEvent({ type: 'delta', delta: '취소 전까지 생성된 본문' });
      resolveStarted();
      await new Promise<void>((resolve) => {
        if (signal?.aborted) {
          resolve();
          return;
        }
        signal?.addEventListener('abort', () => resolve(), { once: true });
      });
    });

    const rendered = await renderHook();
    let generation!: Promise<boolean>;

    await act(async () => {
      generation = rendered.hook.generateSingle('https://youtu.be/partial-cancel', true);
      await started;
    });
    expect(useResultStore.getState().reports[0]).toMatchObject({
      content: '취소 전까지 생성된 본문',
      is_streaming: true,
    });

    await act(async () => {
      rendered.hook.abort();
      await generation;
    });

    expect(useResultStore.getState().reports[0]).toMatchObject({
      content: '취소 전까지 생성된 본문',
      is_streaming: false,
    });
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBeNull();
  });

  it.each([
    ['result', { type: 'result', title: '결과 완료', content: '# 마크다운 결과', html: '' }],
    ['done', { type: 'done', title: '완료 이벤트', content: '평문 결과', html: '' }],
  ] as const)('%s 종료가 html 없는 완료 결과를 스트리밍으로 남기지 않는다', async (_label, finalEvent) => {
    mockStream([finalEvent]);
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.generateSingle('https://youtu.be/html-empty', true);
    });

    expect(useResultStore.getState().reports[0]).toMatchObject({
      content: finalEvent.content,
      html: '',
      is_streaming: false,
    });
    expect(rendered.hook.error).toBeNull();
  });

  it('URL 스트림이 result 없이 종료되어도 로딩을 해제한다', async () => {
    mockStream([{ type: 'meta', youtube_title: '영상 제목' }]);
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.generateSingle('https://youtu.be/abc', true);
    });

    expect(useResultStore.getState().reports).toHaveLength(0);
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBe('생성 결과를 받지 못했습니다.');
  });

  it('사용자 abort 시 오류 없이 빈 임시 카드를 제거하고 로딩을 해제한다', async () => {
    let resolveStarted: () => void = () => undefined;
    const started = new Promise<void>((resolve) => {
      resolveStarted = resolve;
    });

    vi.mocked(generateStream).mockImplementation(async (_req, onEvent, signal) => {
      onEvent({ type: 'meta', youtube_title: '영상 제목' });
      resolveStarted();
      await new Promise<void>((resolve) => {
        if (signal?.aborted) {
          resolve();
          return;
        }
        signal?.addEventListener('abort', () => resolve(), { once: true });
      });
    });

    const rendered = await renderHook();
    let generation!: Promise<boolean>;

    await act(async () => {
      generation = rendered.hook.generateSingle('https://youtu.be/abc', true);
      await started;
    });

    await act(async () => {
      rendered.hook.abort();
      await generation;
    });

    expect(useResultStore.getState().reports).toHaveLength(0);
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBeNull();
  });

  it('A가 시작한 비스트리밍 응답이 늦게 와도 B 보고서에 추가하지 않는다', async () => {
    setAuthSession(authSession('account-a'));
    const pending = deferred<{
      title: string;
      content: string;
      html: string;
      usage: { total_tokens: number };
      elapsed_time: number;
      prompt: string;
    }>();
    vi.mocked(generate).mockImplementationOnce(() => pending.promise);
    const rendered = await renderHook();
    let generation!: Promise<boolean>;

    await act(async () => {
      generation = rendered.hook.generateSingle('https://youtu.be/account-a', false);
      await Promise.resolve();
    });
    expect(rendered.hook.isLoading).toBe(true);

    await act(async () => setAuthSession(authSession('account-b')));
    expect(useResultStore.getState().reports).toEqual([]);

    await act(async () => {
      pending.resolve({
        title: 'A 늦은 결과',
        content: 'A 본문',
        html: '<p>A</p>',
        usage: { total_tokens: 1 },
        elapsed_time: 1,
        prompt: 'A prompt',
      });
      await generation;
    });

    expect(useResultStore.getState().reports).toEqual([]);
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBeNull();
  });

  it('단일 URL 배치는 A 응답 대기 중 B로 전환되면 성공 URL을 반환하지 않는다', async () => {
    setAuthSession(authSession('account-a'));
    const pending = deferred<{
      title: string;
      content: string;
      html: string;
      usage: { total_tokens: number };
      elapsed_time: number;
      prompt: string;
    }>();
    vi.mocked(generate).mockImplementationOnce(() => pending.promise);
    const rendered = await renderHook();
    let generation!: Promise<BatchOutcome>;

    await act(async () => {
      generation = rendered.hook.generateBatchUrls(['https://youtu.be/account-a']);
      await Promise.resolve();
    });

    await act(async () => setAuthSession(authSession('account-b')));
    let outcome: BatchOutcome = { succeededUrls: ['https://youtu.be/account-a'] };
    await act(async () => {
      pending.resolve({
        title: 'A 늦은 결과',
        content: 'A 본문',
        html: '<p>A</p>',
        usage: { total_tokens: 1 },
        elapsed_time: 1,
        prompt: 'A prompt',
      });
      outcome = await generation;
    });

    expect(outcome.succeededUrls).toEqual([]);
    expect(useResultStore.getState().reports).toEqual([]);
  });

  it('부분 성공은 성공 결과만 저장하고 실패 URL과 원인을 안내한다', async () => {
    const urls = ['https://example.com/success', 'https://example.com/failure'];
    vi.mocked(generateBatch).mockResolvedValueOnce({ results: [
      { ...RESPONSE, url: urls[0], success: true },
      { url: urls[1], success: false, error: '자막을 찾을 수 없습니다.' },
    ] });
    useSettingsStore.setState({ detailLevel: 'deep', transcriptLanguage: 'ja', enableWebSearch: true, enableAgentMode: true });
    const rendered = await renderHook();
    let outcome!: BatchOutcome;
    await act(async () => { outcome = await rendered.hook.generateBatchUrls(urls); });

    expect(outcome.succeededUrls).toEqual([urls[0]]);
    expect(useResultStore.getState().reports.map((report) => report.url)).toEqual([urls[0]]);
    expect(toast.warning).toHaveBeenCalledWith('1개 URL 처리 실패', {
      description: `${urls[1]}: 자막을 찾을 수 없습니다.`,
    });
    expect(generateBatch).toHaveBeenCalledWith(urls, 'gpt-test', 'blog_seo', expect.any(Object), undefined, {
      detail_level: 'deep', transcript_language: 'ja', enable_web_search: true, enable_agent_mode: true,
    });
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBeNull();
  });

  it('모두 실패하면 결과를 저장하지 않고 모든 URL별 오류를 남긴다', async () => {
    const urls = ['https://example.com/first', 'https://example.com/second'];
    vi.mocked(generateBatch).mockResolvedValueOnce({ results: urls.map((url, index) => ({ url, success: false, error: `오류 ${index + 1}` })) });
    const rendered = await renderHook();
    let outcome!: BatchOutcome;
    await act(async () => { outcome = await rendered.hook.generateBatchUrls(urls); });

    expect(outcome.succeededUrls).toEqual([]);
    expect(useResultStore.getState().reports).toEqual([]);
    expect(rendered.hook.error).toContain(`${urls[0]}: 오류 1`);
    expect(rendered.hook.error).toContain(`${urls[1]}: 오류 2`);
    expect(rendered.hook.isLoading).toBe(false);
  });

  it('모두 성공하면 모든 성공 URL을 반환한다', async () => {
    const urls = ['https://example.com/first', 'https://example.com/second'];
    vi.mocked(generateBatch).mockResolvedValueOnce({ results: urls.map((url) => ({ ...RESPONSE, url, success: true })) });
    const rendered = await renderHook();
    let outcome!: BatchOutcome;
    await act(async () => { outcome = await rendered.hook.generateBatchUrls(urls); });

    expect(outcome.succeededUrls).toEqual(urls);
    expect(useResultStore.getState().reports).toHaveLength(2);
    expect(toast.warning).not.toHaveBeenCalled();
    expect(rendered.hook.error).toBeNull();
  });

  it('응답에서 누락된 URL은 성공으로 취급하지 않는다', async () => {
    const urls = ['https://example.com/success', 'https://example.com/missing'];
    vi.mocked(generateBatch).mockResolvedValueOnce({ results: [{ ...RESPONSE, url: urls[0], success: true }] });
    const rendered = await renderHook();
    let outcome!: BatchOutcome;
    await act(async () => { outcome = await rendered.hook.generateBatchUrls(urls); });

    expect(outcome.succeededUrls).toEqual([urls[0]]);
    expect(toast.warning).toHaveBeenCalledWith('1개 URL 처리 실패', {
      description: `${urls[1]}: 생성 결과를 받지 못했습니다.`,
    });
  });

  it('이전 계정의 늦은 다중 배치 응답은 결과와 알림을 적용하지 않는다', async () => {
    setAuthSession(authSession('account-a'));
    const urls = ['https://example.com/first', 'https://example.com/second'];
    const pending = deferred<Awaited<ReturnType<typeof generateBatch>>>();
    vi.mocked(generateBatch).mockImplementationOnce(() => pending.promise);
    const rendered = await renderHook();
    let generation!: Promise<BatchOutcome>;
    await act(async () => { generation = rendered.hook.generateBatchUrls(urls); });
    await act(async () => setAuthSession(authSession('account-b')));
    let outcome!: BatchOutcome;
    await act(async () => {
      pending.resolve({ results: [
        { ...RESPONSE, url: urls[0], success: true },
        { url: urls[1], success: false, error: '이전 계정 오류' },
      ] });
      outcome = await generation;
    });

    expect(outcome.succeededUrls).toEqual([]);
    expect(useResultStore.getState().reports).toEqual([]);
    expect(toast.warning).not.toHaveBeenCalled();
    expect(rendered.hook.isLoading).toBe(false);
    expect(rendered.hook.error).toBeNull();
  });

  it('합쳐서 생성에도 선택한 자막 언어를 전달한다', async () => {
    const urls = ['https://example.com/first', 'https://example.com/second'];
    useSettingsStore.setState({ transcriptLanguage: 'en' });
    vi.mocked(generateMerged).mockResolvedValueOnce({ ...RESPONSE, id: 'merged', merged: true, source_videos: [] });
    const rendered = await renderHook();
    await act(async () => { await rendered.hook.generateMergedUrls(urls); });

    expect(generateMerged).toHaveBeenCalledWith(urls, 'gpt-test', 'blog_seo', expect.any(Object), undefined, 'en');
    expect(useResultStore.getState().reports[0].merged).toBe(true);
  });
});

import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { generate, generateStream } from '@/lib/api';
import type { StreamEvent } from '@/lib/types';
import { useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useGenerate } from './useGenerate';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';

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

  it('단일 URL 배치는 A 응답 대기 중 B로 전환되면 false를 반환한다', async () => {
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
      generation = rendered.hook.generateBatchUrls(['https://youtu.be/account-a']);
      await Promise.resolve();
    });

    await act(async () => setAuthSession(authSession('account-b')));
    let succeeded = true;
    await act(async () => {
      pending.resolve({
        title: 'A 늦은 결과',
        content: 'A 본문',
        html: '<p>A</p>',
        usage: { total_tokens: 1 },
        elapsed_time: 1,
        prompt: 'A prompt',
      });
      succeeded = await generation;
    });

    expect(succeeded).toBe(false);
    expect(useResultStore.getState().reports).toEqual([]);
  });
});

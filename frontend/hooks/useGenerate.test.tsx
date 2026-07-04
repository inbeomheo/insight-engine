import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { generateStream } from '@/lib/api';
import type { StreamEvent } from '@/lib/types';
import { useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useGenerate } from './useGenerate';

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

let root: Root | null = null;
let currentHook: GenerateHook | null = null;

function Harness() {
  currentHook = useGenerate();
  return null;
}

async function renderHook() {
  const el = document.createElement('div');
  document.body.appendChild(el);
  root = createRoot(el);
  await act(async () => {
    root!.render(<Harness />);
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
    let generation!: Promise<void>;

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
});

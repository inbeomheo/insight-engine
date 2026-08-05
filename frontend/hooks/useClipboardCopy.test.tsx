import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useClipboardCopy, type ClipboardCopyResult } from './useClipboardCopy';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

type ClipboardCopyHook = ReturnType<typeof useClipboardCopy>;

let root: Root | null = null;
let currentHook: ClipboardCopyHook | null = null;
let execCommandDescriptor: PropertyDescriptor | undefined;

function Harness({
  resetDelayMs,
  onRender,
}: {
  resetDelayMs?: number;
  onRender: (hook: ClipboardCopyHook) => void;
}) {
  const hook = useClipboardCopy({ resetDelayMs });
  useEffect(() => onRender(hook), [hook, onRender]);
  return null;
}

async function renderHook(resetDelayMs?: number) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  const onRender = (hook: ClipboardCopyHook) => {
    currentHook = hook;
  };

  await act(async () => {
    root!.render(<Harness resetDelayMs={resetDelayMs} onRender={onRender} />);
  });

  return {
    get hook() {
      if (!currentHook) throw new Error('hook not rendered');
      return currentHook;
    },
  };
}

function setClipboard(
  writeText?: (text: string) => Promise<void>,
  write?: (items: ClipboardItem[]) => Promise<void>,
) {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: writeText || write ? { writeText, write } : undefined,
  });
}

describe('useClipboardCopy', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    currentHook = null;
    execCommandDescriptor = Object.getOwnPropertyDescriptor(document, 'execCommand');
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    root = null;
    currentHook = null;
    document.body.innerHTML = '';
    Reflect.deleteProperty(navigator, 'clipboard');
    if (execCommandDescriptor) {
      Object.defineProperty(document, 'execCommand', execCommandDescriptor);
    } else {
      Reflect.deleteProperty(document, 'execCommand');
    }
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('텍스트 복사 성공 상태와 반환값을 제공한다', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    const rendered = await renderHook();
    let result!: ClipboardCopyResult;

    await act(async () => {
      result = await rendered.hook.copyText('복사할 내용');
    });

    expect(result).toEqual({ copied: true, isCurrent: true });
    expect(writeText).toHaveBeenCalledWith('복사할 내용');
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBeNull();
  });

  it('키가 있는 복사는 해당 키를 활성 상태로 표시한다', async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.copyText('제목', 'title');
    });

    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('title');
  });

  it('복사 실패 시 false와 오류 상태를 제공한다', async () => {
    setClipboard(vi.fn().mockRejectedValue(new Error('denied')));
    const rendered = await renderHook();
    let result!: ClipboardCopyResult;

    await act(async () => {
      result = await rendered.hook.copyText('복사할 내용');
    });

    expect(result).toEqual({ copied: false, isCurrent: true });
    expect(rendered.hook.status).toBe('error');
    expect(rendered.hook.activeKey).toBeNull();
  });

  it('Clipboard API와 폴백이 없으면 false와 오류 상태를 제공한다', async () => {
    setClipboard();
    const rendered = await renderHook();
    let result!: ClipboardCopyResult;

    await act(async () => {
      result = await rendered.hook.copyText('복사할 내용');
    });

    expect(result).toEqual({ copied: false, isCurrent: true });
    expect(rendered.hook.status).toBe('error');
  });

  it('텍스트 팩토리가 실패하면 클립보드를 호출하지 않고 오류 상태를 제공한다', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const textFactory = vi.fn(() => {
      throw new Error('build failed');
    });
    setClipboard(writeText);
    const rendered = await renderHook();
    let result!: ClipboardCopyResult;

    await act(async () => {
      result = await rendered.hook.copyText(textFactory, 'factory');
    });

    expect(result).toEqual({ copied: false, isCurrent: true });
    expect(textFactory).toHaveBeenCalledOnce();
    expect(writeText).not.toHaveBeenCalled();
    expect(rendered.hook.status).toBe('error');
    expect(rendered.hook.activeKey).toBe('factory');
  });

  it('기본 2초 뒤 상태와 활성 키를 초기화한다', async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.copyText('내용', 'summary');
    });
    await act(async () => vi.advanceTimersByTime(1_999));

    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('summary');

    await act(async () => vi.advanceTimersByTime(1));

    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();
  });

  it('재호출하면 이전 초기화 타이머를 취소하고 새 타이머를 시작한다', async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    const rendered = await renderHook(2_000);

    await act(async () => {
      await rendered.hook.copyText('첫 번째', 'first');
    });
    await act(async () => vi.advanceTimersByTime(1_000));
    await act(async () => {
      await rendered.hook.copyText('두 번째', 'second');
    });
    await act(async () => vi.advanceTimersByTime(1_000));

    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('second');

    await act(async () => vi.advanceTimersByTime(1_000));

    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();
  });

  it('지연된 새 요청은 즉시 이전 피드백을 지우고 완료 후 새 타이머를 시작한다', async () => {
    let resolveSecond: () => void = () => undefined;
    const writeText = vi.fn()
      .mockResolvedValueOnce(undefined)
      .mockImplementationOnce(() => new Promise<void>((resolve) => {
        resolveSecond = resolve;
      }));
    setClipboard(writeText);
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.copyText('첫 번째', 'first');
    });
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('first');

    let secondCopy!: Promise<ClipboardCopyResult>;
    await act(async () => {
      secondCopy = rendered.hook.copyText('두 번째', 'second');
    });

    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();

    await act(async () => vi.advanceTimersByTime(5_000));
    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();

    await act(async () => {
      resolveSecond();
      await secondCopy;
    });
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('second');

    await act(async () => vi.advanceTimersByTime(1_999));
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('second');

    await act(async () => vi.advanceTimersByTime(1));
    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();
  });

  it('동시 복사를 직렬화해 최신 데이터와 피드백을 유지한다', async () => {
    let clipboardValue = '';
    const writes: Array<{ text: string; resolve: () => void }> = [];
    setClipboard(vi.fn().mockImplementation((text: string) => new Promise<void>((resolve) => {
      writes.push({
        text,
        resolve: () => {
          clipboardValue = text;
          resolve();
        },
      });
    })));
    const rendered = await renderHook();
    let firstCopy!: Promise<ClipboardCopyResult>;
    let secondCopy!: Promise<ClipboardCopyResult>;

    await act(async () => {
      firstCopy = rendered.hook.copyText('첫 번째', 'first');
      secondCopy = rendered.hook.copyText('두 번째', 'second');
    });
    expect(writes).toHaveLength(1);
    expect(writes[0].text).toBe('첫 번째');

    await act(async () => {
      writes[0].resolve();
      await firstCopy;
      await Promise.resolve();
    });
    expect(clipboardValue).toBe('첫 번째');
    expect(writes).toHaveLength(2);
    expect(writes[1].text).toBe('두 번째');

    await act(async () => {
      writes[1].resolve();
      await secondCopy;
    });
    expect(clipboardValue).toBe('두 번째');
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('second');
  });

  it('오래된 실패 결과를 최신 요청과 구분한다', async () => {
    let rejectFirst: (error: Error) => void = () => undefined;
    const writeText = vi.fn()
      .mockImplementationOnce(() => new Promise<void>((_resolve, reject) => {
        rejectFirst = reject;
      }))
      .mockResolvedValueOnce(undefined);
    setClipboard(writeText);
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, 'execCommand', {
      configurable: true,
      value: execCommand,
    });
    const rendered = await renderHook();
    let firstCopy!: Promise<ClipboardCopyResult>;
    let secondCopy!: Promise<ClipboardCopyResult>;
    let secondResult!: ClipboardCopyResult;

    await act(async () => {
      firstCopy = rendered.hook.copyText('첫 번째', 'first');
    });
    await act(async () => {
      secondCopy = rendered.hook.copyText('두 번째', 'second');
    });

    let firstResult!: ClipboardCopyResult;
    await act(async () => {
      rejectFirst(new Error('denied'));
      firstResult = await firstCopy;
      secondResult = await secondCopy;
    });

    expect(firstResult).toEqual({ copied: false, isCurrent: false });
    expect(secondResult).toEqual({ copied: true, isCurrent: true });
    expect(execCommand).not.toHaveBeenCalled();
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('second');
  });

  it('두 훅 인스턴스에서도 전역 최신 복사만 실행하고 피드백한다', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    let pair: { first: ClipboardCopyHook; second: ClipboardCopyHook } | null = null;

    function PairHarness() {
      const first = useClipboardCopy({ resetDelayMs: 1_000 });
      const second = useClipboardCopy({ resetDelayMs: 2_000 });
      useEffect(() => {
        pair = { first, second };
      }, [first, second]);
      return null;
    }

    const container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => {
      root!.render(<PairHarness />);
    });
    const getPair = () => {
      if (!pair) throw new Error('hooks not rendered');
      return pair;
    };

    let resolveFirstSource: (text: string) => void = () => undefined;
    let firstCopy!: Promise<ClipboardCopyResult>;
    await act(async () => {
      firstCopy = getPair().first.copyText(
        () => new Promise<string>((resolve) => {
          resolveFirstSource = resolve;
        }),
        'first',
      );
    });
    await act(async () => {
      await getPair().second.copyText('두 번째', 'second');
    });
    let firstResult!: ClipboardCopyResult;
    await act(async () => {
      resolveFirstSource('첫 번째');
      firstResult = await firstCopy;
    });

    expect(firstResult).toEqual({ copied: false, isCurrent: false });
    expect(writeText).toHaveBeenCalledOnce();
    expect(writeText).toHaveBeenCalledWith('두 번째');
    expect(getPair().first.status).toBe('idle');
    expect(getPair().first.activeKey).toBeNull();
    expect(getPair().second.status).toBe('copied');
    expect(getPair().second.activeKey).toBe('second');

    await act(async () => vi.advanceTimersByTime(2_000));

    expect(getPair().second.status).toBe('idle');
    expect(getPair().second.activeKey).toBeNull();
  });

  it('언마운트 시 초기화 타이머를 정리한다', async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.copyText('내용');
    });
    expect(vi.getTimerCount()).toBe(1);

    await act(async () => root!.unmount());
    root = null;

    expect(vi.getTimerCount()).toBe(0);
  });

  it('reset은 상태와 활성 키, 타이머를 즉시 초기화한다', async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    const rendered = await renderHook();

    await act(async () => {
      await rendered.hook.copyText('내용', 'summary');
    });
    expect(vi.getTimerCount()).toBe(1);

    await act(async () => {
      rendered.hook.reset();
    });

    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('reset은 진행 중인 복사 요청의 완료 피드백을 무효화한다', async () => {
    let resolveWrite: () => void = () => undefined;
    setClipboard(vi.fn(() => new Promise<void>((resolve) => {
      resolveWrite = resolve;
    })));
    const rendered = await renderHook();
    let copyPromise!: Promise<ClipboardCopyResult>;

    await act(async () => {
      copyPromise = rendered.hook.copyText('지연 내용', 'pending');
    });
    await act(async () => {
      rendered.hook.reset();
    });

    let result!: ClipboardCopyResult;
    await act(async () => {
      resolveWrite();
      result = await copyPromise;
    });

    expect(result).toEqual({ copied: true, isCurrent: false });
    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('서식 복사는 같은 피드백 타이머 계약을 사용한다', async () => {
    const write = vi.fn().mockResolvedValue(undefined);
    setClipboard(undefined, write);
    const rendered = await renderHook(1_500);
    let result!: ClipboardCopyResult;
    const item = {} as ClipboardItem;

    await act(async () => {
      result = await rendered.hook.copyItems([item], 'rich');
    });

    expect(result).toEqual({ copied: true, isCurrent: true });
    expect(write).toHaveBeenCalledWith([item]);
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('rich');

    await act(async () => vi.advanceTimersByTime(1_500));

    expect(rendered.hook.status).toBe('idle');
    expect(rendered.hook.activeKey).toBeNull();
  });

  it('지연된 서식 복사가 최신 텍스트 복사 피드백을 덮지 않는다', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    let resolveItems: () => void = () => undefined;
    const write = vi.fn(() => new Promise<void>((resolve) => {
      resolveItems = resolve;
    }));
    setClipboard(writeText, write);
    const rendered = await renderHook();
    let externalCopy!: Promise<ClipboardCopyResult>;
    let latestCopy!: Promise<ClipboardCopyResult>;

    await act(async () => {
      externalCopy = rendered.hook.copyItems([{} as ClipboardItem], 'rich');
    });
    await act(async () => {
      latestCopy = rendered.hook.copyText('최신 내용', 'text');
    });

    let externalResult!: ClipboardCopyResult;
    let latestResult!: ClipboardCopyResult;
    await act(async () => {
      resolveItems();
      externalResult = await externalCopy;
      latestResult = await latestCopy;
    });

    expect(externalResult).toEqual({ copied: true, isCurrent: false });
    expect(latestResult).toEqual({ copied: true, isCurrent: true });
    expect(rendered.hook.status).toBe('copied');
    expect(rendered.hook.activeKey).toBe('text');
  });

  it('오래된 비동기 텍스트는 네이티브 복사를 시작하지 않는다', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    const rendered = await renderHook();
    let resolveSource: (text: string) => void = () => undefined;
    let staleCopy!: Promise<ClipboardCopyResult>;

    await act(async () => {
      staleCopy = rendered.hook.copyText(
        () => new Promise<string>((resolve) => {
          resolveSource = resolve;
        }),
        'share',
      );
    });
    await act(async () => {
      await rendered.hook.copyText('최신 제목', 'title');
    });

    let staleResult!: ClipboardCopyResult;
    await act(async () => {
      resolveSource('오래된 공유 링크');
      staleResult = await staleCopy;
    });

    expect(staleResult).toEqual({ copied: false, isCurrent: false });
    expect(writeText).toHaveBeenCalledOnce();
    expect(writeText).toHaveBeenCalledWith('최신 제목');
    expect(rendered.hook.activeKey).toBe('title');
  });
});

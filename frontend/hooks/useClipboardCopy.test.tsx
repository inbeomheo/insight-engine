import { act, useEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useClipboardCopy } from './useClipboardCopy';

type ClipboardHook = ReturnType<typeof useClipboardCopy<string>>;

let root: Root | null = null;
let currentHook: ClipboardHook | null = null;
let originalClipboard: PropertyDescriptor | undefined;

function Harness() {
  const hook = useClipboardCopy<string>(1_000);
  useEffect(() => {
    currentHook = hook;
  }, [hook]);
  return null;
}

async function renderHook(): Promise<ClipboardHook> {
  const container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root!.render(<Harness />));
  if (!currentHook) throw new Error('hook not rendered');
  return currentHook;
}

function setClipboard(writeText?: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: writeText ? { writeText } : undefined,
  });
}

describe('useClipboardCopy', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    originalClipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
    currentHook = null;
  });

  afterEach(async () => {
    if (root) {
      await act(async () => root!.unmount());
      root = null;
    }
    if (originalClipboard) {
      Object.defineProperty(navigator, 'clipboard', originalClipboard);
    } else {
      delete (navigator as unknown as { clipboard?: Clipboard }).clipboard;
    }
    document.body.innerHTML = '';
    currentHook = null;
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('copies text, exposes the active key, and resets feedback', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    let hook = await renderHook();
    let copied = false;

    await act(async () => {
      copied = await hook.copy('복사할 내용', 'card-1');
    });
    hook = currentHook!;

    expect(copied).toBe(true);
    expect(writeText).toHaveBeenCalledWith('복사할 내용');
    expect(hook.status).toBe('copied');
    expect(hook.activeKey).toBe('card-1');

    await act(async () => vi.advanceTimersByTimeAsync(1_000));
    expect(currentHook).toMatchObject({ status: 'idle', activeKey: null });
  });

  it('returns an error state when the clipboard API is unavailable', async () => {
    setClipboard();
    let hook = await renderHook();
    let copied = true;

    await act(async () => {
      copied = await hook.copy('복사할 내용');
    });
    hook = currentHook!;

    expect(copied).toBe(false);
    expect(hook.status).toBe('error');
  });

  it('converts clipboard write failures into a non-throwing error result', async () => {
    setClipboard(vi.fn().mockRejectedValue(new Error('permission denied')));
    let hook = await renderHook();
    let copied = true;

    await act(async () => {
      copied = await hook.copy('복사할 내용', 'card-2');
    });
    hook = currentHook!;

    expect(copied).toBe(false);
    expect(hook).toMatchObject({ status: 'error', activeKey: 'card-2' });
  });
});

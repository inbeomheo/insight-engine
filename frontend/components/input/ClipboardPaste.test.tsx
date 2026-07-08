import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ClipboardPaste from './ClipboardPaste';

let root: Root | null = null;

async function renderClipboardPaste(props: {
  onPasteUrl: (url: string) => void;
  onPasteText: (text: string) => void;
  enabled?: boolean;
}) {
  const el = document.createElement('div');
  document.body.appendChild(el);
  root = createRoot(el);
  await act(async () => {
    root!.render(<ClipboardPaste {...props} />);
  });
}

function pasteText(text: string, target: EventTarget = document) {
  const event = new Event('paste', { bubbles: true, cancelable: true }) as ClipboardEvent;
  Object.defineProperty(event, 'clipboardData', {
    value: { getData: () => text },
  });
  target.dispatchEvent(event);
  return event;
}

describe('ClipboardPaste', () => {
  afterEach(async () => {
    if (root) {
      await act(async () => root!.unmount());
      root = null;
    }
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('URL 붙여넣기를 URL 콜백으로 라우팅한다', async () => {
    const onPasteUrl = vi.fn();
    const onPasteText = vi.fn();
    await renderClipboardPaste({ onPasteUrl, onPasteText });

    const event = pasteText('https://example.com/article');

    expect(event.defaultPrevented).toBe(true);
    expect(onPasteUrl).toHaveBeenCalledWith('https://example.com/article');
    expect(onPasteText).not.toHaveBeenCalled();
  });

  it('대문자 scheme URL도 URL 콜백으로 라우팅한다', async () => {
    const onPasteUrl = vi.fn();
    const onPasteText = vi.fn();
    await renderClipboardPaste({ onPasteUrl, onPasteText });

    const event = pasteText('HTTPS://example.com/article');

    expect(event.defaultPrevented).toBe(true);
    expect(onPasteUrl).toHaveBeenCalledWith('HTTPS://example.com/article');
    expect(onPasteText).not.toHaveBeenCalled();
  });

  it('긴 일반 텍스트 붙여넣기를 텍스트 콜백으로 라우팅한다', async () => {
    const onPasteUrl = vi.fn();
    const onPasteText = vi.fn();
    await renderClipboardPaste({ onPasteUrl, onPasteText });

    const event = pasteText('직접 분석할 긴 텍스트입니다.');

    expect(event.defaultPrevented).toBe(true);
    expect(onPasteText).toHaveBeenCalledWith('직접 분석할 긴 텍스트입니다.');
    expect(onPasteUrl).not.toHaveBeenCalled();
  });

  it('입력 필드 포커스 중에는 기본 붙여넣기를 방해하지 않는다', async () => {
    const onPasteUrl = vi.fn();
    const onPasteText = vi.fn();
    await renderClipboardPaste({ onPasteUrl, onPasteText });

    const input = document.createElement('input');
    document.body.appendChild(input);
    const event = pasteText('https://example.com', input);

    expect(event.defaultPrevented).toBe(false);
    expect(onPasteUrl).not.toHaveBeenCalled();
    expect(onPasteText).not.toHaveBeenCalled();
  });

  it('짧은 일반 텍스트는 기본 붙여넣기를 방해하지 않는다', async () => {
    const onPasteUrl = vi.fn();
    const onPasteText = vi.fn();
    await renderClipboardPaste({ onPasteUrl, onPasteText });

    const event = pasteText('짧음');

    expect(event.defaultPrevented).toBe(false);
    expect(onPasteUrl).not.toHaveBeenCalled();
    expect(onPasteText).not.toHaveBeenCalled();
  });

  it('비활성화 상태에서는 붙여넣기를 무시한다', async () => {
    const onPasteUrl = vi.fn();
    const onPasteText = vi.fn();
    await renderClipboardPaste({ onPasteUrl, onPasteText, enabled: false });

    const event = pasteText('https://example.com');

    expect(event.defaultPrevented).toBe(false);
    expect(onPasteUrl).not.toHaveBeenCalled();
    expect(onPasteText).not.toHaveBeenCalled();
  });
});

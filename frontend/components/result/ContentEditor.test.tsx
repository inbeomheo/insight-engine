import { act, type ComponentProps } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { I18nProvider } from '@/lib/i18n/I18nProvider';
import ContentEditor from './ContentEditor';

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function renderEditor(props: Partial<ComponentProps<typeof ContentEditor>> = {}) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <I18nProvider>
        <ContentEditor
          initialTitle="원본 제목"
          initialContent="원본 본문"
          onSave={vi.fn()}
          onCancel={vi.fn()}
          {...props}
        />
      </I18nProvider>,
    );
  });
}

function findButton(text: string): HTMLButtonElement {
  const button = Array.from(document.querySelectorAll('button')).find((el) =>
    el.textContent?.includes(text),
  );
  if (!button) throw new Error(`button not found: ${text}`);
  return button as HTMLButtonElement;
}

async function setValue(el: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const proto = el instanceof HTMLTextAreaElement
    ? HTMLTextAreaElement.prototype
    : HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
  await act(async () => {
    setter?.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

describe('ContentEditor', () => {
  it('기존 제목/본문을 입력값으로 채운다', async () => {
    await renderEditor();
    expect((document.querySelector('input') as HTMLInputElement).value).toBe('원본 제목');
    expect((document.querySelector('textarea') as HTMLTextAreaElement).value).toBe('원본 본문');
  });

  it('수정한 제목/본문을 onSave로 전달한다', async () => {
    const onSave = vi.fn();
    await renderEditor({ onSave });

    await setValue(document.querySelector('input') as HTMLInputElement, '수정된 제목');
    await setValue(document.querySelector('textarea') as HTMLTextAreaElement, '수정된 본문');

    await act(async () => {
      findButton('저장').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(onSave).toHaveBeenCalledWith({ title: '수정된 제목', content: '수정된 본문' });
  });

  it('취소 버튼은 onCancel만 호출한다', async () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    await renderEditor({ onSave, onCancel });

    await act(async () => {
      findButton('취소').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('Ctrl+Enter로 저장, Esc로 취소된다', async () => {
    const onSave = vi.fn();
    const onCancel = vi.fn();
    await renderEditor({ onSave, onCancel });
    const textarea = document.querySelector('textarea') as HTMLTextAreaElement;

    await act(async () => {
      textarea.dispatchEvent(
        new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true, bubbles: true }),
      );
    });
    expect(onSave).toHaveBeenCalledTimes(1);

    await act(async () => {
      textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});

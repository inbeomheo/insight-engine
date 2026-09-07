import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it } from 'vitest';
import { Dialog, DialogContent, DialogTitle } from './dialog';

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(() => {
  act(() => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

describe('Dialog', () => {
  it('공통 닫기 버튼이 44px 터치 영역을 제공한다', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => {
      root!.render(
        <Dialog open>
          <DialogContent>
            <DialogTitle>테스트</DialogTitle>
          </DialogContent>
        </Dialog>,
      );
    });

    const close = document.querySelector<HTMLElement>('[data-slot="dialog-close"]');
    expect(close).not.toBeNull();
    expect(close?.className).toContain('h-11');
    expect(close?.className).toContain('w-11');
  });
});
